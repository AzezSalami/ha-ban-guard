"""The only module that touches Home Assistant's `http.ban` internals.

Ban Guard needs two things from Home Assistant's HTTP ban machinery:

1. To decide whether a request is blocked. HA's `ban_middleware` evaluates
   `ip_address in ban_manager.ip_bans_lookup`. We replace that dict with a
   subclass whose `__contains__` additionally consults Ban Guard (CIDR bans,
   temporary bans, country rules) and refuses to block protected or
   allowlisted addresses.
2. To see failed logins. HA's `process_wrong_login` increments
   `app[KEY_FAILED_LOGIN_ATTEMPTS][ip]`. We replace that defaultdict with a
   subclass whose `__setitem__` reports increments to Ban Guard.
3. To see successful logins (optional). The auth login flow calls
   `process_success_login(request)`, imported by name into
   `homeassistant.components.auth.login_flow`. We wrap that one reference:
   HA's original always runs first, then Ban Guard is told about the login.
   Websocket re-authentication (every open tab) is not logged as a login.
4. To cut open sessions when an address is banned. The websocket API calls
   `process_success_login(self._request)` once a session authenticates. We
   wrap that reference too and remember the session's transport, so a ban can
   close it at once instead of waiting for the client to reconnect.

Every wrapper catches every exception from Ban Guard and falls back to HA's
own behaviour, so a bug here can never block a request, a login or crash HA.
`check_compatibility` runs at startup; if anything we rely on is missing the
feature is disabled and a repair issue is raised, leaving HA's own banning
untouched.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
import functools
import inspect
from ipaddress import ip_address
import logging
import re
from typing import Any, Protocol
import warnings

from homeassistant.core import HomeAssistant

from .iputil import IPAddress

_LOGGER = logging.getLogger(__name__)

# Large enough that HA's own threshold never triggers while Ban Guard decides.
_DELEGATED_THRESHOLD = 2**31 - 1
_MAX_COUNTER_ENTRIES = 10_000


class HookIncompatibleError(Exception):
    """Home Assistant internals are not what this version expects."""


class BansDisabledError(Exception):
    """`http: ip_ban_enabled` is false, so there is nothing to hook into."""


class Hooks(Protocol):
    """Callbacks implemented by the Ban Guard manager."""

    def hook_active(self) -> bool:
        """Return True if Ban Guard may block addresses not in HA's list."""

    def hook_is_blocked(self, addr: IPAddress, in_ha_list: bool) -> bool:
        """Return the final blocking decision."""

    def hook_failed_login(self, addr: IPAddress) -> None:
        """Report a failed login."""

    def hook_ha_ban(self, addr: IPAddress) -> None:
        """Report that HA added a ban by itself."""

    def hook_login_success(self, addr: IPAddress, user_name: str | None) -> None:
        """Report a successful login through the auth login flow."""

    def hook_session_opened(self, request: Any) -> None:
        """Report an authenticated websocket session (its request)."""

    def hook_error(self, err: BaseException) -> None:
        """Report an unexpected exception inside a hook."""


@dataclass(slots=True)
class Targets:
    """Objects inside Home Assistant that we hook."""

    app: Any
    manager: Any
    ip_ban_cls: type
    key_attempts: Any
    key_threshold: Any
    bans_path: str
    attr_banned_at: str
    login_flow: Any = None  # module whose process_success_login we wrap, if usable
    ws_auth: Any = None  # websocket auth module, for tracking open sessions


class BanLookup(dict[Any, Any]):
    """Replacement for `IpBanManager.ip_bans_lookup`."""

    __slots__ = ("_hooks",)

    def __init__(self, hooks: Hooks, base: dict[Any, Any]) -> None:
        """Init with the existing HA entries."""
        super().__init__(base)
        self._hooks = hooks

    def __contains__(self, key: object) -> bool:
        """Blocking decision used by HA's ban middleware."""
        in_list = dict.__contains__(self, key)
        try:
            return self._hooks.hook_is_blocked(key, in_list)  # type: ignore[arg-type]
        except Exception as err:  # noqa: BLE001 - must never break requests
            _safe_report(self._hooks, err)
            return in_list

    def __bool__(self) -> bool:
        """Make HA's middleware consult us even when its own list is empty."""
        try:
            if self._hooks.hook_active():
                return True
        except Exception as err:  # noqa: BLE001
            _safe_report(self._hooks, err)
        return dict.__len__(self) > 0

    def __setitem__(self, key: Any, value: Any) -> None:
        """HA adds a ban (its own threshold was reached)."""
        dict.__setitem__(self, key, value)
        try:
            self._hooks.hook_ha_ban(key)
        except Exception as err:  # noqa: BLE001
            _safe_report(self._hooks, err)


class FailedLoginCounter(defaultdict[Any, int]):
    """Replacement for `app[KEY_FAILED_LOGIN_ATTEMPTS]`."""

    __slots__ = ("_hooks",)

    def __init__(self, hooks: Hooks, base: dict[Any, int]) -> None:
        """Init with existing counts."""
        super().__init__(int, base)
        self._hooks = hooks

    def __setitem__(self, key: Any, value: int) -> None:
        """Intercept `counter[ip] += 1` from HA's `process_wrong_login`."""
        previous = dict.get(self, key, 0)
        if dict.__len__(self) >= _MAX_COUNTER_ENTRIES:
            dict.clear(self)
        dict.__setitem__(self, key, value)
        if value > previous:
            try:
                self._hooks.hook_failed_login(key)
            except Exception as err:  # noqa: BLE001
                _safe_report(self._hooks, err)

    def __reduce__(self) -> Any:  # pragma: no cover - not pickled in practice
        """Pickle as a plain defaultdict."""
        return (defaultdict, (int, dict(self)))


def _safe_report(hooks: Hooks, err: BaseException) -> None:
    try:
        hooks.hook_error(err)
    except Exception:
        _LOGGER.exception("Ban Guard hook error handler failed")


def _source_contains(func: Any, needle: str) -> bool:
    try:
        return needle in inspect.getsource(func)
    except (OSError, TypeError):
        # Source unavailable (e.g. frozen build); trust the attribute checks.
        return True


def _caller_user_name(frame: Any) -> str | None:
    """Best-effort: the login flow keeps the authenticated user in a local `user`."""
    caller = frame.f_back if frame is not None else None
    try:
        candidate = caller.f_locals.get("user") if caller is not None else None
        name = getattr(candidate, "name", None)
        return name if isinstance(name, str) and name else None
    finally:
        del caller


def _wrap(
    original: Callable[[Any], None],
    hooks: Hooks,
    report: Callable[[Any, Any], None],
) -> Callable[[Any], None]:
    """Run HA's original first, then report to Ban Guard; never raise."""

    @functools.wraps(original)
    def process_success_login(request: Any) -> None:
        original(request)
        frame = inspect.currentframe()
        try:
            report(request, frame)
        except Exception as err:  # noqa: BLE001 - must never break a login or session
            _safe_report(hooks, err)
        finally:
            del frame

    process_success_login.__ban_guard_original__ = original  # type: ignore[attr-defined]
    return process_success_login


def make_success_wrapper(original: Callable[[Any], None], hooks: Hooks) -> Callable[[Any], None]:
    """Wrap the login flow's process_success_login so Ban Guard sees the login."""

    def report(request: Any, frame: Any) -> None:
        remote = getattr(request, "remote", None)
        if remote:
            hooks.hook_login_success(ip_address(remote), _caller_user_name(frame))

    return _wrap(original, hooks, report)


def make_session_wrapper(original: Callable[[Any], None], hooks: Hooks) -> Callable[[Any], None]:
    """Wrap the websocket auth's process_success_login to track open sessions."""

    def report(request: Any, _frame: Any) -> None:
        hooks.hook_session_opened(request)

    return _wrap(original, hooks, report)


def _toggle_wrapper(
    module: Any,
    enabled: bool,
    factory: Callable[[Callable[[Any], None], Hooks], Callable[[Any], None]],
    hooks: Hooks,
) -> None:
    """Install or remove a process_success_login wrapper on one module."""
    if module is None:
        return
    current = module.process_success_login
    original = getattr(current, "__ban_guard_original__", None)
    if enabled and original is None:
        module.process_success_login = factory(current, hooks)
    elif not enabled and original is not None:
        module.process_success_login = original


def _login_flow_module() -> Any:
    """The module that calls process_success_login after a credential login."""
    try:
        from homeassistant.components.auth import login_flow  # noqa: PLC0415
    except ImportError:
        return None
    if not callable(getattr(login_flow, "process_success_login", None)):
        return None
    if not _source_contains(login_flow, "process_success_login(request)"):
        return None
    return login_flow


def _ws_auth_module() -> Any:
    """The websocket auth phase, which calls process_success_login per session."""
    try:
        from homeassistant.components.websocket_api import auth as ws_auth  # noqa: PLC0415
    except ImportError:
        return None
    if not callable(getattr(ws_auth, "process_success_login", None)):
        return None
    if not _source_contains(ws_auth, "process_success_login(self._request)"):
        return None
    return ws_auth


_COUNTER_INCREMENT = re.compile(r"\[KEY_FAILED_LOGIN_ATTEMPTS\]\[\s*\w+\s*\]\s*\+=\s*1")


def _source_matches(obj: Any, pattern: re.Pattern[str]) -> bool:
    try:
        return pattern.search(inspect.getsource(obj)) is not None
    except (OSError, TypeError):
        # Source unavailable (e.g. frozen build); trust the attribute checks.
        return True


def check_compatibility(hass: HomeAssistant) -> Targets:
    """Verify HA internals. Does blocking I/O (source reads): run in executor."""
    try:
        from homeassistant.components.http import ban as ha_ban  # noqa: PLC0415
    except ImportError as err:
        raise HookIncompatibleError("homeassistant.components.http.ban missing") from err

    required = (
        "KEY_BAN_MANAGER",
        "KEY_FAILED_LOGIN_ATTEMPTS",
        "KEY_LOGIN_THRESHOLD",
        "IpBan",
        "IpBanManager",
        "IP_BANS_FILE",
        "ATTR_BANNED_AT",
        "ban_middleware",
        "process_wrong_login",
    )
    missing = [name for name in required if not hasattr(ha_ban, name)]
    if missing:
        raise HookIncompatibleError(f"missing attributes: {', '.join(missing)}")

    if not _source_contains(ha_ban.ban_middleware, "in ip_bans_lookup"):
        raise HookIncompatibleError("ban_middleware no longer checks ip_bans_lookup")
    # HA counts failures with `app[KEY_FAILED_LOGIN_ATTEMPTS][ip] += 1`. Up to
    # 2026.10 this lived in process_wrong_login; 2026.11 moved it into a
    # helper. Look for the increment anywhere in the module, not one function.
    if not _source_matches(ha_ban, _COUNTER_INCREMENT):
        raise HookIncompatibleError("failed logins are no longer counted per address")

    http = getattr(hass, "http", None)
    app = getattr(http, "app", None)
    if app is None:
        raise HookIncompatibleError("hass.http.app unavailable")
    if ha_ban.KEY_BAN_MANAGER not in app:
        raise BansDisabledError
    manager = app[ha_ban.KEY_BAN_MANAGER]
    if not isinstance(getattr(manager, "ip_bans_lookup", None), dict):
        raise HookIncompatibleError("IpBanManager.ip_bans_lookup is not a dict")
    if not isinstance(app.get(ha_ban.KEY_FAILED_LOGIN_ATTEMPTS), dict):
        raise HookIncompatibleError("failed login counter is not a dict")
    if not isinstance(app.get(ha_ban.KEY_LOGIN_THRESHOLD), int):
        raise HookIncompatibleError("login threshold is not an int")
    path = getattr(manager, "path", None) or hass.config.path(ha_ban.IP_BANS_FILE)
    return Targets(
        app=app,
        manager=manager,
        ip_ban_cls=ha_ban.IpBan,
        key_attempts=ha_ban.KEY_FAILED_LOGIN_ATTEMPTS,
        key_threshold=ha_ban.KEY_LOGIN_THRESHOLD,
        bans_path=str(path),
        attr_banned_at=ha_ban.ATTR_BANNED_AT,
        login_flow=_login_flow_module(),
        ws_auth=_ws_auth_module(),
    )


def _set_app_state(app: Any, key: Any, value: Any) -> None:
    """Set state on a started aiohttp app without the deprecation noise."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        app[key] = value


class Hook:
    """Install and remove the wrappers."""

    def __init__(self, targets: Targets, hooks: Hooks) -> None:
        """Init."""
        self.targets = targets
        self._hooks = hooks
        self._original_threshold: int | None = None
        self._delegating = False

    @property
    def installed(self) -> bool:
        """True if our lookup is still in place."""
        return isinstance(self.targets.manager.ip_bans_lookup, BanLookup)

    @property
    def login_logging_available(self) -> bool:
        """True if successful logins can be observed on this HA version."""
        return self.targets.login_flow is not None

    def set_login_logging(self, enabled: bool) -> None:
        """Install or remove the login flow wrapper."""
        _toggle_wrapper(self.targets.login_flow, enabled, make_success_wrapper, self._hooks)

    @property
    def session_tracking_available(self) -> bool:
        """True if open websocket sessions can be tracked on this HA version."""
        return self.targets.ws_auth is not None

    def set_session_tracking(self, enabled: bool) -> None:
        """Install or remove the websocket session wrapper."""
        _toggle_wrapper(self.targets.ws_auth, enabled, make_session_wrapper, self._hooks)

    def install(self) -> None:
        """Install (or re-install) the lookup and counter wrappers."""
        manager = self.targets.manager
        if not isinstance(manager.ip_bans_lookup, BanLookup):
            manager.ip_bans_lookup = BanLookup(self._hooks, manager.ip_bans_lookup)
        app = self.targets.app
        counter = app.get(self.targets.key_attempts)
        if not isinstance(counter, FailedLoginCounter):
            _set_app_state(
                app, self.targets.key_attempts, FailedLoginCounter(self._hooks, counter or {})
            )

    def delegate_threshold(self, enabled: bool) -> None:
        """Make HA count every failure but leave the ban decision to Ban Guard."""
        app = self.targets.app
        key = self.targets.key_threshold
        if enabled and not self._delegating:
            self._original_threshold = int(app[key])
            _set_app_state(app, key, _DELEGATED_THRESHOLD)
            self._delegating = True
        elif not enabled and self._delegating:
            _set_app_state(app, key, self._original_threshold)
            self._delegating = False

    @property
    def original_threshold(self) -> int:
        """HA's configured login threshold."""
        if self._original_threshold is not None:
            return self._original_threshold
        return int(self.targets.app[self.targets.key_threshold])

    def uninstall(self) -> None:
        """Restore HA's plain objects."""
        try:
            self.delegate_threshold(False)
            self.set_login_logging(False)
            self.set_session_tracking(False)
            manager = self.targets.manager
            if isinstance(manager.ip_bans_lookup, BanLookup):
                manager.ip_bans_lookup = dict(manager.ip_bans_lookup.items())
            app = self.targets.app
            counter = app.get(self.targets.key_attempts)
            if isinstance(counter, FailedLoginCounter):
                _set_app_state(
                    app, self.targets.key_attempts, defaultdict(int, dict(counter.items()))
                )
        except Exception:
            _LOGGER.exception("Failed to restore Home Assistant ban internals")

    def base_entries(self) -> dict[Any, Any]:
        """HA's own in-memory bans."""
        return dict(dict.items(self.targets.manager.ip_bans_lookup))

    def set_base(self, addr: IPAddress, banned_at: Any) -> None:
        """Add an entry to HA's in-memory list without triggering hook_ha_ban."""
        entry = self.targets.ip_ban_cls(addr, banned_at)
        dict.__setitem__(self.targets.manager.ip_bans_lookup, addr, entry)

    def remove_base(self, addr: IPAddress) -> None:
        """Remove an entry from HA's in-memory list."""
        dict.pop(self.targets.manager.ip_bans_lookup, addr, None)
