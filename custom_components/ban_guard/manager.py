"""Ban Guard core: bans, allowlist, failed-login protection and HA sync."""

from __future__ import annotations

import asyncio
from collections import deque
from collections.abc import Callable, Iterable
import contextlib
from datetime import datetime, timedelta
import logging
import time
from typing import Any

from homeassistant.components import persistent_notification
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_call_later, async_track_time_interval
from homeassistant.helpers.http import current_request
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from . import bansfile
from .activity import ActivityLog
from .const import (
    ACT_ALLOW,
    ACT_ALLOWLISTED_FAILURE,
    ACT_BAN,
    ACT_BLOCKED,
    ACT_DISALLOW,
    ACT_EXPIRED,
    ACT_FAILED_LOGIN,
    ACT_REFUSED,
    ACT_UNBAN,
    BLOCKED_LOG_INTERVAL_SECONDS,
    CONF_ALLOWLIST_REFRESH_MINUTES,
    CONF_DOH_ENABLED,
    CONF_DOH_URL,
    CONF_GEOIP_EDITION,
    CONF_GEOIP_ENABLED,
    CONF_GEOIP_MAX_MB,
    CONF_LOG_BLOCKED,
    CONF_LOG_MAX_ENTRIES,
    CONF_LOG_RETENTION_DAYS,
    CONF_NOTIFY_ALLOWLISTED,
    CONF_NOTIFY_PERSISTENT,
    CONF_NPM_ACCESS_LIST_ID,
    CONF_NPM_ENABLED,
    CONF_NPM_SECRET,
    CONF_NPM_URL,
    CONF_NPM_USERNAME,
    CONF_NPM_VERIFY_SSL,
    CONF_PROTECTION_ENABLED,
    CONF_RDNS_ENABLED,
    CONF_REPEATED_FAILURES,
    DOMAIN,
    EVENT_BAN_GUARD,
    EVT_ALLOWLISTED_FAILURE,
    EVT_BAN,
    EVT_REPEATED_FAILURES,
    EVT_UNBAN,
    ISSUE_BANS_DISABLED,
    ISSUE_GEOIP_FAILED,
    ISSUE_HOOK_ERROR,
    ISSUE_HOOK_INCOMPATIBLE,
    ISSUE_NPM_FAILED,
    MAX_IMPORT_ITEMS,
    MAX_REASON_LENGTH,
    SIGNAL_UPDATE,
    SOURCE_AUTOMATIC,
    SOURCE_HOME_ASSISTANT,
    SOURCE_IMPORTED,
    SOURCES,
    STORAGE_KEY_DATA,
    STORAGE_VERSION,
)
from .enrichment import GeoIP, GeoIPError, Resolver
from .guard import LockoutGuard
from .ha_hook import BansDisabledError, Hook, HookIncompatibleError, check_compatibility
from .iputil import (
    InvalidTargetError,
    IPAddress,
    IPNetwork,
    NetworkSet,
    is_hostname,
    is_single,
    network_key,
    normalize_address,
    parse_address,
    parse_network,
    sanitize_path,
    sanitize_user_agent,
)
from .models import AllowEntry, Ban, Offense, parse_datetime_value
from .npm import NPMClient, NPMError
from .secret import SecretBox
from .settings import (
    ProtectionSettings,
    SettingsError,
    country_rules,
    merged,
    protection_settings,
)

_LOGGER = logging.getLogger(__name__)

OFFENSE_DECAY = timedelta(days=30)
EXPIRY_INTERVAL = timedelta(seconds=30)
MAINTENANCE_INTERVAL = timedelta(minutes=5)
GEOIP_CHECK_INTERVAL = timedelta(days=1)
HOOK_ERROR_LIMIT = 20
HOOK_ERROR_WINDOW = 60.0
REVERT_DELAY = 2.0
EXPORT_VERSION = 1
EXPORTABLE_SETTINGS_EXCLUDE = {CONF_NPM_SECRET, "npm_password"}


class BanGuardError(HomeAssistantError):
    """A user-facing error with a translation key."""

    def __init__(self, key: str, **placeholders: str) -> None:
        """Init."""
        super().__init__(
            translation_domain=DOMAIN,
            translation_key=key,
            translation_placeholders=placeholders or None,
        )
        self.key = key
        self.placeholders = placeholders

    def __str__(self) -> str:
        """Readable fallback when translations are not loaded."""
        detail = ", ".join(f"{k}={v}" for k, v in self.placeholders.items())
        return f"{self.key}: {detail}" if detail else self.key


class BanGuardManager:
    """Owns all Ban Guard state for one config entry."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Init."""
        self.hass = hass
        self.entry = entry
        self.options: dict[str, Any] = merged(entry.options)
        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, STORAGE_KEY_DATA, private=True
        )
        self.guard = LockoutGuard(hass)
        self.activity = ActivityLog(
            hass,
            int(self.options[CONF_LOG_MAX_ENTRIES]),
            int(self.options[CONF_LOG_RETENTION_DAYS]),
        )
        self.secret = SecretBox(hass)
        self.bans: dict[str, Ban] = {}
        self.allow: dict[str, AllowEntry] = {}
        self.offenses: dict[str, Offense] = {}
        self.last_ban: dict[str, Any] | None = None
        self._single: dict[IPAddress, Ban] = {}
        self._cidr = NetworkSet()
        self._cidr_bans: dict[str, Ban] = {}
        self._allow_set = NetworkSet()
        self._failures: dict[IPAddress, deque[datetime]] = {}
        self._recent_failures: deque[datetime] = deque(maxlen=10_000)
        self._blocked_logged: dict[IPAddress, float] = {}
        self._hook_errors: deque[float] = deque(maxlen=HOOK_ERROR_LIMIT)
        self._unsubs: list[CALLBACK_TYPE] = []
        self._yaml_lock = asyncio.Lock()
        self.hook: Hook | None = None
        self.hook_status = "not_started"
        self.protection: ProtectionSettings = protection_settings({})
        self.country_allow: frozenset[str] = frozenset()
        self.country_deny: frozenset[str] = frozenset()
        self.geoip: GeoIP | None = None
        self.resolver = Resolver(hass, rdns=False, doh=False, doh_url="")
        self.npm_status: dict[str, Any] = {"enabled": False}
        self._apply_options()

    # ------------------------------------------------------------------ setup

    def _apply_options(self) -> None:
        opts = self.options
        try:
            self.protection = protection_settings(opts)
        except SettingsError:
            _LOGGER.error("Invalid protection settings, using defaults")
            self.protection = protection_settings({})
        try:
            self.country_allow, self.country_deny = country_rules(opts)
        except SettingsError:
            _LOGGER.error("Invalid country rules, ignoring them")
            self.country_allow, self.country_deny = frozenset(), frozenset()
        self.activity.configure(int(opts[CONF_LOG_MAX_ENTRIES]), int(opts[CONF_LOG_RETENTION_DAYS]))
        self.resolver = Resolver(
            self.hass,
            rdns=bool(opts[CONF_RDNS_ENABLED]),
            doh=bool(opts[CONF_DOH_ENABLED]),
            doh_url=str(opts[CONF_DOH_URL]),
        )

    @property
    def protection_enabled(self) -> bool:
        """True if Ban Guard decides on failed-login bans."""
        return bool(self.options[CONF_PROTECTION_ENABLED])

    async def async_setup(self) -> None:
        """Load state and hook into HA."""
        await self._async_load()
        await self.activity.async_load()
        await self.guard.async_refresh()
        await self.guard.async_refresh_admins()
        await self._async_setup_hook()
        await self._async_reconcile_yaml()
        self._rebuild_indexes()
        self._unsubs.append(
            async_track_time_interval(
                self.hass, self._async_expiry_tick, EXPIRY_INTERVAL, name="ban_guard expiry"
            )
        )
        self._unsubs.append(
            async_track_time_interval(
                self.hass,
                self._async_maintenance_tick,
                MAINTENANCE_INTERVAL,
                name="ban_guard maintenance",
            )
        )
        refresh = max(1, int(self.options[CONF_ALLOWLIST_REFRESH_MINUTES]))
        self._unsubs.append(
            async_track_time_interval(
                self.hass,
                self._async_allowlist_tick,
                timedelta(minutes=refresh),
                name="ban_guard allowlist refresh",
            )
        )
        if self.options[CONF_GEOIP_ENABLED]:
            self.geoip = GeoIP(
                self.hass,
                str(self.options[CONF_GEOIP_EDITION]),
                int(self.options[CONF_GEOIP_MAX_MB]),
            )
            self.entry.async_create_background_task(
                self.hass, self._async_load_geoip(), "ban_guard geoip load"
            )
            self._unsubs.append(
                async_track_time_interval(
                    self.hass,
                    self._async_geoip_tick,
                    GEOIP_CHECK_INTERVAL,
                    name="ban_guard geoip refresh",
                )
            )
        self.entry.async_create_background_task(
            self.hass, self._async_refresh_allowlist(), "ban_guard allowlist resolve"
        )
        await self._async_purge_expired()

    async def _async_setup_hook(self) -> None:
        try:
            targets = await self.hass.async_add_executor_job(check_compatibility, self.hass)
        except BansDisabledError:
            self.hook_status = "ip_ban_disabled"
            ir.async_create_issue(
                self.hass,
                DOMAIN,
                ISSUE_BANS_DISABLED,
                is_fixable=False,
                severity=ir.IssueSeverity.WARNING,
                translation_key=ISSUE_BANS_DISABLED,
            )
            return
        except HookIncompatibleError as err:
            _LOGGER.warning("Ban Guard request hook disabled: %s", err)
            self.hook_status = "incompatible"
            ir.async_create_issue(
                self.hass,
                DOMAIN,
                ISSUE_HOOK_INCOMPATIBLE,
                is_fixable=False,
                severity=ir.IssueSeverity.ERROR,
                translation_key=ISSUE_HOOK_INCOMPATIBLE,
                translation_placeholders={"detail": str(err)},
            )
            return
        ir.async_delete_issue(self.hass, DOMAIN, ISSUE_HOOK_INCOMPATIBLE)
        ir.async_delete_issue(self.hass, DOMAIN, ISSUE_BANS_DISABLED)
        self.hook = Hook(targets, self)
        self.hook.install()
        self.hook.delegate_threshold(self.protection_enabled)
        self.hook_status = "active"

    async def async_unload(self) -> None:
        """Remove hooks and timers, flush state."""
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()
        if self.hook is not None:
            self.hook.uninstall()
            self.hook = None
        self.hook_status = "unloaded"
        await self.activity.async_save_now()
        await self._async_save()

    @property
    def hook_active_flag(self) -> bool:
        """True if requests are being checked."""
        return self.hook is not None and self.hook_status == "active"

    # ------------------------------------------------------------- persistence

    async def _async_load(self) -> None:
        data = await self._store.async_load() or {}
        for raw in data.get("bans", []):
            try:
                ban = Ban.from_dict(raw)
            except (KeyError, ValueError, TypeError):
                _LOGGER.warning("Skipping invalid stored ban %s", raw)
                continue
            self.bans[ban.key] = ban
        for raw in data.get("allowlist", []):
            try:
                entry = AllowEntry.from_dict(raw)
            except (KeyError, ValueError, TypeError):
                continue
            self.allow[entry.value] = entry
        for ip, raw in (data.get("offenses") or {}).items():
            try:
                self.offenses[ip] = Offense.from_dict(raw)
            except (KeyError, ValueError, TypeError):
                continue
        self.last_ban = data.get("last_ban")

    def _data(self) -> dict[str, Any]:
        return {
            "bans": [b.as_dict() for b in self.bans.values()],
            "allowlist": [a.as_dict() for a in self.allow.values()],
            "offenses": {ip: o.as_dict() for ip, o in self.offenses.items()},
            "last_ban": self.last_ban,
        }

    async def _async_save(self) -> None:
        await self._store.async_save(self._data())

    def _rebuild_indexes(self) -> None:
        single: dict[IPAddress, Ban] = {}
        cidr = NetworkSet()
        cidr_bans: dict[str, Ban] = {}
        for ban in self.bans.values():
            if ban.single:
                single[ban.network.network_address] = ban
            else:
                cidr.add(ban.network)
                cidr_bans[ban.key] = ban
        self._single, self._cidr, self._cidr_bans = single, cidr, cidr_bans
        allow = NetworkSet()
        for entry in self.allow.values():
            for net in entry.networks():
                allow.add(net)
        self._allow_set = allow

    def _changed(self) -> None:
        self._rebuild_indexes()
        async_dispatcher_send(self.hass, SIGNAL_UPDATE)

    # -------------------------------------------------------- ip_bans.yaml sync

    @property
    def _bans_path(self) -> str:
        if self.hook is not None:
            return self.hook.targets.bans_path
        return self.hass.config.path("ip_bans.yaml")

    @staticmethod
    def _in_yaml(ban: Ban) -> bool:
        """Permanent single-address bans are mirrored to ip_bans.yaml.

        Temporary and CIDR bans live only in Ban Guard's storage, so if Ban
        Guard is removed they do not become permanent (or, for CIDR, break
        HA's loader, which only understands single addresses).
        """
        return ban.single and ban.permanent

    async def _async_reconcile_yaml(self) -> None:
        """Import bans HA knows about; drop permanent bans removed from the file."""
        try:
            async with self._yaml_lock:
                on_disk = await self.hass.async_add_executor_job(
                    bansfile.read_bans, self._bans_path
                )
        except HomeAssistantError:
            return
        changed = False
        for ip, banned_at in on_disk.items():
            if ip in self.bans:
                continue
            self.bans[ip] = Ban(
                network=parse_network(ip),
                reason="",
                source=SOURCE_HOME_ASSISTANT,
                created_by=None,
                created_at=banned_at,
            )
            changed = True
        for key, ban in list(self.bans.items()):
            if self._in_yaml(ban) and key not in on_disk:
                del self.bans[key]
                self.activity.add(ACT_UNBAN, key, detail="removed_from_ip_bans_yaml")
                changed = True
        if self.hook is not None:
            for ban in self.bans.values():
                if self._in_yaml(ban):
                    self.hook.set_base(ban.network.network_address, ban.created_at)
        if changed:
            await self._async_save()

    async def _async_write_yaml(self, add: Iterable[Ban] = (), remove: Iterable[str] = ()) -> None:
        additions = {b.key: b.created_at for b in add if self._in_yaml(b)}
        removals = list(remove)
        if not additions and not removals:
            return
        async with self._yaml_lock:
            await self.hass.async_add_executor_job(
                bansfile.update_bans, self._bans_path, additions, removals
            )
        if self.hook is not None:
            for key in removals:
                self.hook.remove_base(parse_address(key))
            for key, banned_at in additions.items():
                self.hook.set_base(parse_address(key), banned_at)

    # ------------------------------------------------------------- hook API

    def hook_active(self) -> bool:
        """Consult Ban Guard even if HA's list is empty."""
        return bool(self._single or len(self._cidr) or self._country_rules_active)

    @property
    def _country_rules_active(self) -> bool:
        return bool(
            self.geoip is not None
            and self.geoip.loaded
            and (self.country_allow or self.country_deny)
        )

    def country_of(self, ip: str) -> str | None:
        """ISO country code for an IP, if GeoIP is loaded."""
        if self.geoip is None or not self.geoip.loaded:
            return None
        try:
            info = self.geoip.lookup(parse_address(ip))
        except InvalidTargetError:
            return None
        return info["country"] if info else None

    def _country_denied(self, addr: IPAddress) -> str | None:
        if not self._country_rules_active or self.geoip is None:
            return None
        info = self.geoip.lookup(addr)
        if info is None:
            return None
        country = str(info["country"])
        if country in self.country_deny:
            return country
        if self.country_allow and country not in self.country_allow:
            return country
        return None

    def is_allowlisted(self, addr: IPAddress) -> bool:
        """True if the address is on the allowlist."""
        return normalize_address(addr) in self._allow_set

    def match_ban(self, addr: IPAddress, now: datetime | None = None) -> Ban | None:
        """Return the active Ban Guard ban covering addr."""
        addr = normalize_address(addr)
        now = now or dt_util.utcnow()
        ban = self._single.get(addr)
        if ban is not None and not ban.expired(now):
            return ban
        net = self._cidr.match(addr)
        if net is not None:
            cidr_ban = self._cidr_bans.get(str(net))
            if cidr_ban is not None and not cidr_ban.expired(now):
                return cidr_ban
        return None

    def hook_is_blocked(self, addr: IPAddress, in_list: bool) -> bool:
        """Blocking decision for HA's ban middleware."""
        addr = normalize_address(addr)
        reason: str | None = None
        if self.match_ban(addr) is not None:
            reason = "ban"
        elif in_list:
            reason = "ha_ban"
        elif (country := self._country_denied(addr)) is not None:
            reason = f"country:{country}"
        if reason is None:
            return False
        if self.is_allowlisted(addr) or self.guard.is_protected(addr):
            return False
        self._log_blocked(addr, reason)
        return True

    def _request_info(self) -> tuple[str | None, str | None]:
        request = current_request.get()
        if request is None:
            return None, None
        return (
            sanitize_path(request.path),
            sanitize_user_agent(request.headers.get("User-Agent")),
        )

    def _log_blocked(self, addr: IPAddress, reason: str) -> None:
        if not self.options[CONF_LOG_BLOCKED]:
            return
        now = time.monotonic()
        last = self._blocked_logged.get(addr)
        if last is not None and now - last < BLOCKED_LOG_INTERVAL_SECONDS:
            return
        if len(self._blocked_logged) > 10_000:
            self._blocked_logged.clear()
        self._blocked_logged[addr] = now
        path, agent = self._request_info()
        self.activity.add(ACT_BLOCKED, str(addr), path=path, user_agent=agent, detail=reason)

    def hook_failed_login(self, addr: IPAddress) -> None:
        """HA counted a failed login."""
        addr = normalize_address(addr)
        ip = str(addr)
        path, agent = self._request_info()
        now = dt_util.utcnow()
        if self.is_allowlisted(addr):
            if self.options[CONF_NOTIFY_ALLOWLISTED]:
                self.activity.add(ACT_ALLOWLISTED_FAILURE, ip, path=path, user_agent=agent)
                self._fire(EVT_ALLOWLISTED_FAILURE, ip, path=path)
                self._notify(
                    "allowlisted_failure",
                    f"Failed login from allowlisted address {ip}.",
                    "Ban Guard: failed login from allowlisted address",
                )
            return
        self.activity.add(ACT_FAILED_LOGIN, ip, path=path, user_agent=agent)
        self._recent_failures.append(now)
        async_dispatcher_send(self.hass, SIGNAL_UPDATE)
        if not self.protection_enabled or self.hook is None:
            return
        threshold, window = self.protection.rule_for(addr)
        if threshold == 0:
            return
        history = self._failures.setdefault(addr, deque(maxlen=1000))
        history.append(now)
        while history and history[0] < now - window:
            history.popleft()
        if len(self._failures) > 50_000:
            self._prune_failures(now)
        count = len(history)
        repeated = int(self.options[CONF_REPEATED_FAILURES])
        if 0 < repeated < threshold and count == repeated:
            self._fire(EVT_REPEATED_FAILURES, ip, count=count)
            self._notify(
                f"repeated_{ip}",
                f"{count} failed logins from {ip} in the last "
                f"{int(window.total_seconds() // 60)} minutes.",
                "Ban Guard: repeated failed logins",
            )
        if count < threshold:
            return
        history.clear()
        if self.guard.is_protected(addr):
            self.activity.add(ACT_REFUSED, ip, detail="protected")
            return
        offense = self._next_offense(ip, now)
        duration = self.protection.duration_for(offense)
        self.entry.async_create_background_task(
            self.hass,
            self._async_auto_ban(addr, count, window, offense, duration),
            f"ban_guard auto ban {ip}",
        )

    def _prune_failures(self, now: datetime) -> None:
        cutoff = now - timedelta(days=1)
        for key in [k for k, v in self._failures.items() if not v or v[-1] < cutoff]:
            del self._failures[key]

    def _next_offense(self, ip: str, now: datetime) -> int:
        current = self.offenses.get(ip)
        if current is None or now - current.last > OFFENSE_DECAY:
            current = Offense(0, now)
        current = Offense(current.count + 1, now)
        self.offenses[ip] = current
        return current.count

    async def _async_auto_ban(
        self,
        addr: IPAddress,
        count: int,
        window: timedelta,
        offense: int,
        duration: timedelta | None,
    ) -> None:
        minutes = int(window.total_seconds() // 60)
        try:
            await self.async_ban(
                str(addr),
                reason=f"{count} failed logins in {minutes} min",
                source=SOURCE_AUTOMATIC,
                user=None,
                duration=duration,
                offense=offense,
            )
        except BanGuardError as err:
            _LOGGER.info("Automatic ban of %s refused: %s", addr, err)

    def hook_ha_ban(self, addr: IPAddress) -> None:
        """HA's own threshold added a ban."""
        addr = normalize_address(addr)
        key = str(addr)
        if self.is_allowlisted(addr) or self.guard.is_protected(addr):
            self.activity.add(ACT_REFUSED, key, detail="ha_ban_reverted")
            if self.hook is not None:
                self.hook.remove_base(addr)

            @callback
            def _revert(_now: datetime) -> None:
                # HA appends to ip_bans.yaml right after this hook returns;
                # remove the line once that write has landed.
                self.entry.async_create_background_task(
                    self.hass, self._async_write_yaml(remove=[key]), "ban_guard revert"
                )

            self._unsubs.append(async_call_later(self.hass, REVERT_DELAY, _revert))
            return
        if key in self.bans:
            return
        ban = Ban(
            network=parse_network(key),
            reason="Home Assistant login threshold",
            source=SOURCE_HOME_ASSISTANT,
            created_by=None,
            created_at=dt_util.utcnow(),
        )
        self.bans[key] = ban
        self._after_ban(ban)
        self.entry.async_create_background_task(self.hass, self._async_save(), "ban_guard save")

    def hook_error(self, err: BaseException) -> None:
        """Count hook errors; disable the hook if they keep happening."""
        now = time.monotonic()
        self._hook_errors.append(now)
        _LOGGER.error("Ban Guard request hook error: %s", err, exc_info=err)
        if (
            len(self._hook_errors) >= HOOK_ERROR_LIMIT
            and now - self._hook_errors[0] < HOOK_ERROR_WINDOW
            and self.hook is not None
        ):
            _LOGGER.error("Too many hook errors, disabling the Ban Guard request hook")
            self.hook.uninstall()
            self.hook = None
            self.hook_status = "error"
            ir.async_create_issue(
                self.hass,
                DOMAIN,
                ISSUE_HOOK_ERROR,
                is_fixable=False,
                severity=ir.IssueSeverity.ERROR,
                translation_key=ISSUE_HOOK_ERROR,
                translation_placeholders={"detail": str(err)[:200]},
            )

    # ---------------------------------------------------------- notifications

    def _fire(self, kind: str, ip: str, **extra: Any) -> None:
        data = {"type": kind, "ip": ip}
        data.update({k: v for k, v in extra.items() if v is not None})
        self.hass.bus.async_fire(EVENT_BAN_GUARD, data)

    def _notify(self, notification_id: str, message: str, title: str) -> None:
        if not self.options[CONF_NOTIFY_PERSISTENT]:
            return
        persistent_notification.async_create(
            self.hass, message, title, f"{DOMAIN}_{notification_id}"
        )

    # --------------------------------------------------------------- actions

    async def _async_user_name(self, user_id: str | None) -> str | None:
        if user_id is None:
            return None
        user = await self.hass.auth.async_get_user(user_id)
        return user.name if user is not None and user.name else user_id

    def _check_lockout(self, network: IPNetwork, requester: IPAddress | None) -> None:
        conflicts = self.guard.conflicts(network, requester)
        if conflicts:
            first = conflicts[0]
            raise BanGuardError(
                f"protected_{first.reason}",
                ip=network_key(network),
                protected=str(first.network),
            )

    async def async_ban(
        self,
        target: str,
        *,
        reason: str = "",
        source: str,
        user: str | None,
        duration: timedelta | None = None,
        expires_at: datetime | None = None,
        requester: IPAddress | None = None,
        offense: int = 0,
        save: bool = True,
    ) -> Ban:
        """Ban an address or network."""
        try:
            network = parse_network(target)
        except InvalidTargetError as err:
            raise BanGuardError("invalid_ip", ip=target) from err
        if source not in SOURCES:
            raise BanGuardError("invalid_source", source=source)
        self._check_lockout(network, requester)
        if is_single(network) and network.network_address in self._allow_set:
            raise BanGuardError("allowlisted", ip=network_key(network))
        now = dt_util.utcnow()
        if duration is not None:
            expires_at = now + duration
        if expires_at is not None and expires_at <= now:
            raise BanGuardError("expiry_in_past", ip=network_key(network))
        ban = Ban(
            network=network,
            reason=reason.strip()[:MAX_REASON_LENGTH],
            source=source,
            created_by=await self._async_user_name(user),
            created_at=now,
            expires_at=expires_at,
            offense=offense,
        )
        previous = self.bans.get(ban.key)
        self.bans[ban.key] = ban
        remove: list[str] = []
        if previous is not None and self._in_yaml(previous) and not self._in_yaml(ban):
            remove.append(previous.key)
        await self._async_write_yaml(add=[ban], remove=remove)
        self._after_ban(ban)
        if save:
            await self._async_save()
        return ban

    def _after_ban(self, ban: Ban) -> None:
        detail = ban.reason or None
        self.activity.add(ACT_BAN, ban.key, detail=detail, user=ban.created_by)
        self.last_ban = {
            "ip": ban.key,
            "reason": ban.reason,
            "source": ban.source,
            "created_at": ban.created_at.isoformat(),
            "expires_at": ban.expires_at.isoformat() if ban.expires_at else None,
            "country": self.country_of(str(ban.network.network_address)),
        }
        self._fire(
            EVT_BAN,
            ban.key,
            reason=ban.reason,
            source=ban.source,
            expires_at=ban.expires_at.isoformat() if ban.expires_at else None,
        )
        until = (
            f" until {dt_util.as_local(ban.expires_at).strftime('%Y-%m-%d %H:%M')}"
            if ban.expires_at
            else ""
        )
        self._notify(
            f"ban_{ban.key}",
            f"{ban.key} was banned{until}. {ban.reason}".strip(),
            "Ban Guard: address banned",
        )
        self._changed()
        self._schedule_npm_sync()

    async def async_unban(
        self, targets: Iterable[str], *, user: str | None, kind: str = ACT_UNBAN
    ) -> list[Ban]:
        """Remove bans. Unknown targets raise."""
        removed: list[Ban] = []
        keys: list[str] = []
        for target in targets:
            try:
                key = network_key(parse_network(target))
            except InvalidTargetError as err:
                raise BanGuardError("invalid_ip", ip=target) from err
            keys.append(key)
        missing = [k for k in keys if k not in self.bans]
        if missing:
            raise BanGuardError("not_banned", ip=", ".join(missing))
        name = await self._async_user_name(user)
        for key in keys:
            ban = self.bans.pop(key)
            removed.append(ban)
            self._failures.pop(ban.network.network_address, None)
            self.activity.add(kind, key, user=name)
            self._fire(EVT_UNBAN, key, expired=kind == ACT_EXPIRED)
        await self._async_write_yaml(remove=[b.key for b in removed if self._in_yaml(b)])
        await self._async_save()
        self._changed()
        self._schedule_npm_sync()
        return removed

    async def async_restore(self, bans: Iterable[dict[str, Any]]) -> None:
        """Re-create bans from their serialised form (undo of unban)."""
        restored = [Ban.from_dict(b) for b in bans]
        now = dt_util.utcnow()
        for ban in restored:
            if ban.expired(now):
                continue
            self.bans[ban.key] = ban
            self.activity.add(ACT_BAN, ban.key, detail="restored")
        await self._async_write_yaml(add=restored)
        await self._async_save()
        self._changed()
        self._schedule_npm_sync()

    async def _async_purge_expired(self) -> list[Ban]:
        now = dt_util.utcnow()
        expired = [b.key for b in self.bans.values() if b.expired(now)]
        if not expired:
            return []
        return await self.async_unban(expired, user=None, kind=ACT_EXPIRED)

    async def async_purge_expired(self) -> int:
        """Lift expired bans now; returns count."""
        return len(await self._async_purge_expired())

    async def async_allow(
        self, value: str, *, comment: str = "", user: str | None, save: bool = True
    ) -> AllowEntry:
        """Add an IP, CIDR or hostname to the allowlist."""
        text = value.strip().lower()
        try:
            text = network_key(parse_network(text))
        except InvalidTargetError:
            if not is_hostname(text):
                raise BanGuardError("invalid_allow", value=value) from None
        entry = AllowEntry(
            value=text,
            comment=comment.strip()[:MAX_REASON_LENGTH],
            created_by=await self._async_user_name(user),
            created_at=dt_util.utcnow(),
        )
        if entry.is_hostname:
            entry.resolved = await self.resolver.async_resolve(text)
            entry.resolved_at = dt_util.utcnow()
        self.allow[text] = entry
        self.activity.add(ACT_ALLOW, text, user=entry.created_by, detail=comment or None)
        self._rebuild_indexes()
        if save:
            await self._async_save()
        self._changed()
        return entry

    async def async_disallow(self, value: str, *, user: str | None) -> AllowEntry:
        """Remove an allowlist entry."""
        text = value.strip().lower()
        with contextlib.suppress(InvalidTargetError):
            text = network_key(parse_network(text))
        entry = self.allow.pop(text, None)
        if entry is None:
            raise BanGuardError("not_allowlisted", value=value)
        self.activity.add(ACT_DISALLOW, text, user=await self._async_user_name(user))
        await self._async_save()
        self._changed()
        return entry

    # ------------------------------------------------------------- periodic

    async def _async_expiry_tick(self, _now: datetime) -> None:
        await self._async_purge_expired()
        async_dispatcher_send(self.hass, SIGNAL_UPDATE)

    async def _async_maintenance_tick(self, _now: datetime) -> None:
        await self.guard.async_refresh_admins()
        if self.hook is not None and not self.hook.installed:
            _LOGGER.debug("Ban list object was replaced by HA, re-installing hook")
            self.hook.install()
            await self._async_reconcile_yaml()
        self.activity.purge()
        self._prune_failures(dt_util.utcnow())

    async def _async_allowlist_tick(self, _now: datetime) -> None:
        await self._async_refresh_allowlist()

    async def _async_refresh_allowlist(self) -> None:
        changed = False
        for entry in list(self.allow.values()):
            if not entry.is_hostname:
                continue
            resolved = await self.resolver.async_resolve(entry.value)
            entry.resolved_at = dt_util.utcnow()
            if resolved and resolved != entry.resolved:
                entry.resolved = resolved
                changed = True
        if changed:
            await self._async_save()
            self._changed()

    async def _async_load_geoip(self) -> None:
        if self.geoip is None:
            return
        try:
            await self.geoip.async_load()
        except GeoIPError as err:
            _LOGGER.warning("GeoIP database unavailable: %s", err)
            ir.async_create_issue(
                self.hass,
                DOMAIN,
                ISSUE_GEOIP_FAILED,
                is_fixable=False,
                severity=ir.IssueSeverity.WARNING,
                translation_key=ISSUE_GEOIP_FAILED,
                translation_placeholders={"detail": str(err)[:200]},
            )
            return
        ir.async_delete_issue(self.hass, DOMAIN, ISSUE_GEOIP_FAILED)
        async_dispatcher_send(self.hass, SIGNAL_UPDATE)

    async def _async_geoip_tick(self, _now: datetime) -> None:
        if self.geoip is None:
            return
        try:
            await self.geoip.async_refresh_if_stale()
        except GeoIPError as err:
            _LOGGER.warning("GeoIP refresh failed: %s", err)

    # ------------------------------------------------------------------ NPM

    def _schedule_npm_sync(self) -> None:
        if not self.options.get(CONF_NPM_ENABLED):
            return
        self.entry.async_create_background_task(
            self.hass, self.async_npm_sync(), "ban_guard npm sync"
        )

    async def async_npm_client(self) -> NPMClient | None:
        """Build an NPM client from options (decrypting the password)."""
        opts = self.options
        token = opts.get(CONF_NPM_SECRET)
        if not opts.get(CONF_NPM_ENABLED) or not token:
            return None
        password = await self.secret.async_decrypt(str(token))
        if password is None:
            return None
        return NPMClient(
            self.hass,
            str(opts[CONF_NPM_URL]),
            str(opts[CONF_NPM_USERNAME]),
            password,
            bool(opts[CONF_NPM_VERIFY_SSL]),
        )

    async def async_npm_sync(self) -> None:
        """Push active bans to the configured NPM access list."""
        client = await self.async_npm_client()
        if client is None:
            self.npm_status = {"enabled": bool(self.options.get(CONF_NPM_ENABLED))}
            return
        now = dt_util.utcnow()
        denied = [b.key for b in self.bans.values() if not b.expired(now)]
        try:
            count = await client.async_sync(int(self.options[CONF_NPM_ACCESS_LIST_ID]), denied)
        except NPMError as err:
            self.npm_status = {"enabled": True, "ok": False, "error": err.key}
            ir.async_create_issue(
                self.hass,
                DOMAIN,
                ISSUE_NPM_FAILED,
                is_fixable=False,
                severity=ir.IssueSeverity.WARNING,
                translation_key=ISSUE_NPM_FAILED,
                translation_placeholders={"detail": err.key},
            )
            return
        ir.async_delete_issue(self.hass, DOMAIN, ISSUE_NPM_FAILED)
        self.npm_status = {
            "enabled": True,
            "ok": True,
            "count": count,
            "synced_at": now.isoformat(),
        }

    # -------------------------------------------------------------- queries

    def is_under_attack(self) -> bool:
        """True if failures crossed the configured rate."""
        cutoff = dt_util.utcnow() - self.protection.attack_window
        recent = sum(1 for ts in self._recent_failures if ts >= cutoff)
        return recent >= self.protection.attack_threshold

    def recent_failure_count(self) -> int:
        """Failures inside the attack window."""
        cutoff = dt_util.utcnow() - self.protection.attack_window
        return sum(1 for ts in self._recent_failures if ts >= cutoff)

    def active_bans(self) -> list[Ban]:
        """Bans that have not expired."""
        now = dt_util.utcnow()
        return [b for b in self.bans.values() if not b.expired(now)]

    def geo(self, ip: str) -> dict[str, Any] | None:
        """GeoIP info for an IP."""
        if self.geoip is None or not self.geoip.loaded:
            return None
        try:
            return self.geoip.lookup(parse_address(ip))
        except InvalidTargetError:
            return None

    def ban_view(self, ban: Ban) -> dict[str, Any]:
        """Serialise a ban for the UI."""
        data = ban.as_dict()
        data["single"] = ban.single
        geo = self.geo(str(ban.network.network_address)) if ban.single else None
        data["country"] = geo["country"] if geo else None
        data["city"] = geo["city"] if geo else None
        data["in_ip_bans_yaml"] = self._in_yaml(ban)
        return data

    def status(self) -> dict[str, Any]:
        """Feature status for the UI and diagnostics."""
        return {
            "hook": self.hook_status,
            "protection_enabled": self.protection_enabled,
            "ha_login_threshold": self.hook.original_threshold if self.hook else None,
            "geoip": {
                "enabled": self.geoip is not None,
                "loaded": bool(self.geoip and self.geoip.loaded),
                "edition": self.options[CONF_GEOIP_EDITION],
                "error": self.geoip.last_error if self.geoip else None,
            },
            "rdns": bool(self.options[CONF_RDNS_ENABLED]),
            "doh": bool(self.options[CONF_DOH_ENABLED]),
            "npm": self.npm_status,
            "country_rules": {
                "allow": sorted(self.country_allow),
                "deny": sorted(self.country_deny),
            },
            "under_attack": self.is_under_attack(),
        }

    async def async_history(self, ip: str) -> dict[str, Any]:
        """Everything known about one IP."""
        key = ip
        try:
            key = network_key(parse_network(ip))
        except InvalidTargetError as err:
            raise BanGuardError("invalid_ip", ip=ip) from err
        hostname = None
        try:
            hostname = await self.resolver.async_reverse(parse_address(key))
        except InvalidTargetError:
            hostname = None
        offense = self.offenses.get(key)
        return {
            "ip": key,
            "ban": self.ban_view(self.bans[key]) if key in self.bans else None,
            "geo": self.geo(key),
            "hostname": hostname,
            "offenses": offense.count if offense else 0,
            "allowlisted": self._is_allowlisted_text(key),
            "activity": [e.as_dict() for e in self.activity.entries(ip=key, limit=200)],
        }

    def _is_allowlisted_text(self, key: str) -> bool:
        try:
            return self.is_allowlisted(parse_address(key))
        except InvalidTargetError:
            return False

    # ------------------------------------------------------- import / export

    def export_data(self) -> dict[str, Any]:
        """JSON backup of bans, allowlist and settings."""
        return {
            "format": "ban_guard",
            "version": EXPORT_VERSION,
            "exported_at": dt_util.utcnow().isoformat(),
            "bans": [b.as_dict() for b in self.bans.values()],
            "allowlist": [{"value": a.value, "comment": a.comment} for a in self.allow.values()],
            "settings": {
                k: v for k, v in self.entry.options.items() if k not in EXPORTABLE_SETTINGS_EXCLUDE
            },
        }

    def validate_import(self, data: Any, requester: IPAddress | None = None) -> dict[str, Any]:
        """Validate a backup and describe what importing it would change."""
        if not isinstance(data, dict) or data.get("format") != "ban_guard":
            raise BanGuardError("import_invalid_format")
        if int(data.get("version", 0)) > EXPORT_VERSION:
            raise BanGuardError("import_unsupported_version")
        bans_in = data.get("bans") or []
        allow_in = data.get("allowlist") or []
        if not isinstance(bans_in, list) or not isinstance(allow_in, list):
            raise BanGuardError("import_invalid_format")
        if len(bans_in) + len(allow_in) > MAX_IMPORT_ITEMS:
            raise BanGuardError("import_too_large", limit=str(MAX_IMPORT_ITEMS))
        now = dt_util.utcnow()
        preview: dict[str, Any] = {
            "bans_new": [],
            "bans_existing": [],
            "bans_expired": [],
            "allow_new": [],
            "allow_existing": [],
            "errors": [],
            "settings": {},
        }
        for index, raw in enumerate(bans_in):
            try:
                if not isinstance(raw, dict):
                    raise ValueError("not an object")
                ban = Ban.from_dict(raw)
                parse_datetime_value(raw.get("expires_at"))
                self._check_lockout(ban.network, requester)
            except BanGuardError as err:
                preview["errors"].append(
                    {"section": "bans", "index": index, "error": err.key, **err.placeholders}
                )
                continue
            except (KeyError, ValueError, TypeError) as err:
                preview["errors"].append(
                    {"section": "bans", "index": index, "error": "invalid", "detail": str(err)}
                )
                continue
            if ban.expired(now):
                preview["bans_expired"].append(ban.key)
            elif ban.key in self.bans:
                preview["bans_existing"].append(ban.key)
            else:
                preview["bans_new"].append(ban.as_dict())
        for index, raw in enumerate(allow_in):
            value = str(raw.get("value", "")) if isinstance(raw, dict) else ""
            text = value.strip().lower()
            try:
                text = network_key(parse_network(text))
            except InvalidTargetError:
                if not is_hostname(text):
                    preview["errors"].append(
                        {"section": "allowlist", "index": index, "error": "invalid_allow"}
                    )
                    continue
            target = "allow_existing" if text in self.allow else "allow_new"
            preview[target].append(
                {"value": text, "comment": str(raw.get("comment") or "")[:MAX_REASON_LENGTH]}
            )
        settings_in = data.get("settings") or {}
        if not isinstance(settings_in, dict):
            raise BanGuardError("import_invalid_format")
        from .const import DEFAULT_OPTIONS  # noqa: PLC0415

        candidate = {
            k: v
            for k, v in settings_in.items()
            if k in DEFAULT_OPTIONS and k not in EXPORTABLE_SETTINGS_EXCLUDE
        }
        try:
            protection_settings(candidate)
            country_rules(candidate)
        except SettingsError as err:
            preview["errors"].append({"section": "settings", "error": err.key})
            candidate = {}
        preview["settings"] = {k: v for k, v in candidate.items() if self.options.get(k) != v}
        return preview

    async def async_import(
        self,
        data: Any,
        *,
        user: str | None,
        requester: IPAddress | None = None,
        include_settings: bool = True,
    ) -> dict[str, Any]:
        """Apply a validated backup. Returns the preview that was applied."""
        preview = self.validate_import(data, requester)
        name = await self._async_user_name(user)
        added: list[Ban] = []
        for raw in preview["bans_new"]:
            ban = Ban.from_dict(raw)
            ban.source = SOURCE_IMPORTED
            ban.created_by = name
            self.bans[ban.key] = ban
            added.append(ban)
            self.activity.add(ACT_BAN, ban.key, detail="imported", user=name)
        for item in preview["allow_new"]:
            entry = AllowEntry(
                value=item["value"],
                comment=item["comment"],
                created_by=name,
                created_at=dt_util.utcnow(),
            )
            if entry.is_hostname:
                entry.resolved = await self.resolver.async_resolve(entry.value)
                entry.resolved_at = dt_util.utcnow()
            self.allow[entry.value] = entry
            self.activity.add(ACT_ALLOW, entry.value, detail="imported", user=name)
        await self._async_write_yaml(add=added)
        await self._async_save()
        self._changed()
        self._schedule_npm_sync()
        if include_settings and preview["settings"]:
            options = dict(self.entry.options)
            options.update(preview["settings"])
            self.hass.config_entries.async_update_entry(self.entry, options=options)
        return preview

    # ---------------------------------------------------------------- misc

    def subscribe_activity(self, listener: Callable[[Any], None]) -> Callable[[], None]:
        """Subscribe to activity entries."""
        return self.activity.subscribe(listener)
