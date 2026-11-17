"""Compatibility check, fail-safe fallback and real HTTP blocking."""

from __future__ import annotations

import ipaddress
from socket import herror
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.typing import ClientSessionGenerator

from custom_components.ban_guard import ha_hook
from custom_components.ban_guard.const import (
    DOMAIN,
    ISSUE_BANS_DISABLED,
    ISSUE_HOOK_ERROR,
    ISSUE_HOOK_INCOMPATIBLE,
    SOURCE_MANUAL,
)
from custom_components.ban_guard.ha_hook import (
    BanLookup,
    FailedLoginCounter,
    HookIncompatibleError,
    check_compatibility,
)
from custom_components.ban_guard.manager import BanGuardManager
from homeassistant.components.http import ban as ha_ban
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from .conftest import setup_deps


async def _setup(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, data={}, options={})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_http_request_blocked(
    hass: HomeAssistant, manager: BanGuardManager, hass_client_no_auth: ClientSessionGenerator
) -> None:
    client = await hass_client_no_auth()
    headers = {"X-Forwarded-For": "198.51.100.9"}
    resp = await client.get("/api/", headers=headers)
    assert resp.status != 403
    await manager.async_ban("198.51.100.0/24", source=SOURCE_MANUAL, user=None)
    resp = await client.get("/api/", headers=headers)
    assert resp.status == 403
    resp = await client.get("/api/", headers={"X-Forwarded-For": "198.51.101.9"})
    assert resp.status != 403


async def test_failed_login_via_ha_code_path(hass: HomeAssistant, manager: BanGuardManager) -> None:
    """Drive HA's real process_wrong_login with a fake request."""
    request = MagicMock()
    request.app = hass.http.app
    request.remote = "198.51.100.33"
    request.headers = {"user-agent": "bot"}
    request.rel_url = "/auth/login_flow"
    with patch("homeassistant.components.http.ban.gethostbyaddr", side_effect=herror):
        for _ in range(5):
            await ha_ban.process_wrong_login(request)
    await hass.async_block_till_done()
    assert "198.51.100.33" in manager.bans
    ha_ban.process_success_login(request)


async def test_incompatible_ha_falls_back(hass: HomeAssistant) -> None:
    await setup_deps(hass)
    with patch.object(ha_ban, "ban_middleware", lambda request, handler: None):
        entry = await _setup(hass)
    manager: BanGuardManager = entry.runtime_data
    assert manager.hook_status == "incompatible"
    assert ir.async_get(hass).async_get_issue(DOMAIN, ISSUE_HOOK_INCOMPATIBLE)
    # HA's own objects are untouched.
    assert type(hass.http.app[ha_ban.KEY_BAN_MANAGER].ip_bans_lookup) is dict
    # Banning still writes ip_bans.yaml.
    await manager.async_ban("198.51.100.1", source=SOURCE_MANUAL, user=None)
    path = hass.config.path("ip_bans.yaml")
    assert "198.51.100.1" in await hass.async_add_executor_job(_read, path)
    assert manager.status()["ha_login_threshold"] is None


def _read(path: str) -> str:
    with open(path, encoding="utf8") as fh:
        return fh.read()


async def test_bans_disabled(hass: HomeAssistant) -> None:
    await setup_deps(hass, {"ip_ban_enabled": False})
    entry = await _setup(hass)
    assert entry.runtime_data.hook_status == "ip_ban_disabled"
    assert ir.async_get(hass).async_get_issue(DOMAIN, ISSUE_BANS_DISABLED)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda mod, app: delattr(mod, "IpBanManager"),
        lambda mod, app: setattr(app[mod.KEY_BAN_MANAGER], "ip_bans_lookup", []),
        lambda mod, app: app._state.__setitem__(mod.KEY_FAILED_LOGIN_ATTEMPTS, None),
        lambda mod, app: app._state.__setitem__(mod.KEY_LOGIN_THRESHOLD, "5"),
    ],
)
async def test_compat_checks(hass: HomeAssistant, mutate: Any) -> None:
    await setup_deps(hass)
    with patch.object(ha_ban, "IpBanManager", ha_ban.IpBanManager):
        mutate(ha_ban, hass.http.app)
        with pytest.raises(HookIncompatibleError):
            await hass.async_add_executor_job(check_compatibility, hass)


async def test_compat_no_http(hass: HomeAssistant) -> None:
    with pytest.raises(HookIncompatibleError):
        check_compatibility(hass)


async def test_compat_source_unavailable() -> None:
    assert ha_hook._source_contains(len, "anything") is True


class _BrokenHooks:
    def __init__(self) -> None:
        self.errors: list[BaseException] = []

    def hook_active(self) -> bool:
        raise RuntimeError("boom")

    def hook_is_blocked(self, addr: Any, in_list: bool) -> bool:
        raise RuntimeError("boom")

    def hook_failed_login(self, addr: Any) -> None:
        raise RuntimeError("boom")

    def hook_ha_ban(self, addr: Any) -> None:
        raise RuntimeError("boom")

    def hook_error(self, err: BaseException) -> None:
        self.errors.append(err)
        if len(self.errors) > 3:
            raise RuntimeError("error handler broken too")


def test_wrappers_never_raise() -> None:
    hooks = _BrokenHooks()
    ip = ipaddress.ip_address("198.51.100.1")
    lookup = BanLookup(hooks, {ip: "ban"})
    assert ip in lookup  # falls back to dict membership
    assert ipaddress.ip_address("198.51.100.2") not in lookup
    assert bool(lookup) is True
    assert bool(BanLookup(hooks, {})) is False
    lookup[ipaddress.ip_address("198.51.100.3")] = "x"
    counter = FailedLoginCounter(hooks, {})
    counter[ip] += 1  # error handler raises here and is swallowed
    assert counter[ip] == 1
    assert len(hooks.errors) >= 4


def test_counter_is_bounded() -> None:
    hooks = MagicMock()
    counter = FailedLoginCounter(hooks, {})
    with patch.object(ha_hook, "_MAX_COUNTER_ENTRIES", 3):
        for i in range(5):
            counter[ipaddress.ip_address(f"10.0.0.{i}")] += 1
    assert len(counter) <= 3


async def test_repeated_hook_errors_disable_hook(
    hass: HomeAssistant, manager: BanGuardManager
) -> None:
    with patch.object(manager, "match_ban", side_effect=RuntimeError("bug")):
        table = hass.http.app[ha_ban.KEY_BAN_MANAGER].ip_bans_lookup
        for _ in range(25):
            assert ipaddress.ip_address("198.51.100.1") not in table
    assert manager.hook_status == "error"
    assert ir.async_get(hass).async_get_issue(DOMAIN, ISSUE_HOOK_ERROR)
    assert type(hass.http.app[ha_ban.KEY_BAN_MANAGER].ip_bans_lookup) is dict


async def test_hook_reinstalled_after_replacement(
    hass: HomeAssistant, manager: BanGuardManager
) -> None:
    ha_manager = hass.http.app[ha_ban.KEY_BAN_MANAGER]
    ha_manager.ip_bans_lookup = {}  # what HA's async_load does on (re)load
    assert manager.hook is not None and not manager.hook.installed
    await manager._async_maintenance_tick(None)  # type: ignore[arg-type]
    assert manager.hook.installed


async def test_uninstall_survives_errors(manager: BanGuardManager) -> None:
    assert manager.hook is not None
    with patch.object(manager.hook, "delegate_threshold", side_effect=RuntimeError):
        manager.hook.uninstall()  # logged, not raised
