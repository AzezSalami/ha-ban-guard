"""Ban enforcement status and closing open sessions on a ban."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import aiohttp
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.typing import (
    ClientSessionGenerator,
    WebSocketGenerator,
)

from custom_components.ban_guard import ha_hook
from custom_components.ban_guard.const import ACT_BLOCKED, DOMAIN, SOURCE_MANUAL
from custom_components.ban_guard.manager import BanGuardError, BanGuardManager
from homeassistant.components.http import ban as ha_ban
from homeassistant.components.websocket_api import auth as ws_auth
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .conftest import setup_deps

IP = "198.51.100.9"


async def _admin_uses(hass: HomeAssistant, user: Any, ip: str) -> None:
    token = await hass.auth.async_create_refresh_token(user, "client")
    token.last_used_ip = ip
    token.last_used_at = dt_util.utcnow()


# ----------------------------------------------------------------- enforcement


async def test_enforced(manager: BanGuardManager) -> None:
    ban = await manager.async_ban(IP, source=SOURCE_MANUAL, user=None)
    assert manager.enforcement(ban) == {
        "enforced": True,
        "partial": False,
        "reason": None,
        "protected": None,
        "exempt": [],
    }
    assert manager.ban_view(ban)["enforcement"]["enforced"] is True


async def test_not_enforced_when_allowlisted_later(manager: BanGuardManager) -> None:
    ban = await manager.async_ban(IP, source=SOURCE_MANUAL, user=None)
    await manager.async_allow("198.51.100.0/24", user=None)
    status = manager.enforcement(ban)
    assert status["enforced"] is False
    assert status["reason"] == "allowlisted"


async def test_not_enforced_when_admin_uses_address_later(
    hass: HomeAssistant, manager: BanGuardManager, hass_admin_user: Any
) -> None:
    ban = await manager.async_ban(IP, source=SOURCE_MANUAL, user=None)
    await _admin_uses(hass, hass_admin_user, IP)
    await manager.guard.async_refresh_admins()
    status = manager.enforcement(ban)
    assert status["enforced"] is False
    assert status["reason"] == "protected_admin"
    assert status["protected"] == f"{IP}/32"
    # The request hook agrees: the address is not blocked.
    lookup = hass.http.app[ha_ban.KEY_BAN_MANAGER].ip_bans_lookup
    import ipaddress

    assert ipaddress.ip_address(IP) not in lookup


async def test_admin_cache_refreshed_before_ban(
    hass: HomeAssistant, manager: BanGuardManager, hass_admin_user: Any
) -> None:
    """A just-used admin address is refused even if the 5-minute cache is stale."""
    await _admin_uses(hass, hass_admin_user, IP)
    assert manager.guard.admin_ips() == []  # cache not refreshed yet
    with pytest.raises(BanGuardError) as err:
        await manager.async_ban(IP, source=SOURCE_MANUAL, user=None)
    assert err.value.key == "protected_admin"


async def test_range_partly_exempt(manager: BanGuardManager) -> None:
    await manager.async_allow("198.51.100.5", user=None)
    await manager.async_allow("vpn.example.com", user=None)
    manager.allow["vpn.example.com"].resolved = ["198.51.100.77", "203.0.113.1"]
    ban = await manager.async_ban("198.51.100.0/24", source=SOURCE_MANUAL, user=None)
    status = manager.enforcement(ban)
    assert status["enforced"] is True
    assert status["partial"] is True
    assert status["reason"] == "partial"
    assert status["exempt"] == ["198.51.100.5", "198.51.100.77"]


async def test_not_enforced_when_hook_inactive(hass: HomeAssistant) -> None:
    await setup_deps(hass, {"ip_ban_enabled": False})
    entry = MockConfigEntry(domain=DOMAIN, data={}, options={})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    manager: BanGuardManager = entry.runtime_data
    ban = await manager.async_ban(IP, source=SOURCE_MANUAL, user=None)
    status = manager.enforcement(ban)
    assert status["enforced"] is False
    assert status["reason"] == "hook_ip_ban_disabled"
    assert manager.status()["session_closing"] is False


async def test_sensor_counts_unenforced(hass: HomeAssistant, manager: BanGuardManager) -> None:
    await manager.async_ban(IP, source=SOURCE_MANUAL, user=None)
    await manager.async_ban("198.51.100.10", source=SOURCE_MANUAL, user=None)
    await manager.async_allow("198.51.100.10", user=None)
    await hass.async_block_till_done()
    state = hass.states.get("sensor.ban_guard_active_bans")
    assert state.attributes["not_enforced"] == 1


async def test_websocket_ban_returns_enforcement(
    hass: HomeAssistant, manager: BanGuardManager, hass_ws_client: WebSocketGenerator
) -> None:
    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id({"type": "ban_guard/ban", "ip": IP})
    msg = await ws.receive_json()
    while msg["type"] != "result":
        msg = await ws.receive_json()
    assert msg["result"]["ban"]["enforcement"]["enforced"] is True


# -------------------------------------------------------------------- sessions


def _session(hass: HomeAssistant, ip: str) -> MagicMock:
    """Register a fake authenticated websocket session through HA's ws auth module."""
    request = MagicMock()
    request.remote = ip
    request.transport = MagicMock()
    request.transport.is_closing.return_value = False
    ws_auth.process_success_login(request)
    return request.transport


async def test_sessions_closed_on_ban(hass: HomeAssistant, manager: BanGuardManager) -> None:
    assert manager.status()["session_closing"] is True
    banned = _session(hass, IP)
    banned_too = _session(hass, IP)
    other = _session(hass, "198.51.101.1")
    host = _session(hass, "192.168.1.10")  # this HA host: protected
    await manager.async_ban(IP, source=SOURCE_MANUAL, user=None)
    banned.close.assert_called_once()
    banned_too.close.assert_called_once()
    other.close.assert_not_called()
    host.close.assert_not_called()
    entry = manager.activity.entries(types={ACT_BLOCKED})[0]
    assert entry.ip == IP
    assert entry.detail == "session_closed:2"

    # A range ban closes every session inside it, except allowlisted ones.
    inside = _session(hass, "203.0.113.20")
    allowed = _session(hass, "203.0.113.21")
    await manager.async_allow("203.0.113.21", user=None)
    await manager.async_ban("203.0.113.0/24", source=SOURCE_MANUAL, user=None)
    inside.close.assert_called_once()
    allowed.close.assert_not_called()


async def test_sessions_pruned_and_bounded(hass: HomeAssistant, manager: BanGuardManager) -> None:
    stale = _session(hass, IP)
    stale.is_closing.return_value = True
    await manager._async_maintenance_tick(None)  # type: ignore[arg-type]
    assert not manager._sessions
    # Already closed between registration and ban: skipped, not closed twice.
    gone = _session(hass, IP)
    gone.is_closing.return_value = True
    await manager.async_ban(IP, source=SOURCE_MANUAL, user=None)
    gone.close.assert_not_called()
    # No transport (already torn down): ignored.
    request = MagicMock(remote=IP, transport=None)
    ws_auth.process_success_login(request)
    assert not manager._sessions
    with patch("custom_components.ban_guard.manager.MAX_TRACKED_SESSIONS", 1):
        _session(hass, "198.51.101.1")
        _session(hass, "198.51.101.2")
    assert len(manager._sessions) == 1


async def test_close_errors_are_contained(hass: HomeAssistant, manager: BanGuardManager) -> None:
    broken = _session(hass, IP)
    broken.close.side_effect = RuntimeError("socket gone")
    await manager.async_ban(IP, source=SOURCE_MANUAL, user=None)  # must not raise
    assert not manager._sessions


async def test_restore_and_import_close_sessions(
    hass: HomeAssistant, manager: BanGuardManager
) -> None:
    await manager.async_ban(IP, source=SOURCE_MANUAL, user=None)
    removed = await manager.async_unban([IP], user=None)
    restored = _session(hass, IP)
    await manager.async_restore([b.as_dict() for b in removed])
    restored.close.assert_called_once()

    imported = _session(hass, "198.51.101.5")
    backup = manager.export_data()
    backup["bans"].append({"ip": "198.51.101.5"})
    await manager.async_import(backup, user=None)
    imported.close.assert_called_once()


async def test_session_wrapper_lifecycle(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    original = ws_auth.process_success_login.__ban_guard_original__
    await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert ws_auth.process_success_login.__ban_guard_original__ is original  # no double wrap
    assert await hass.config_entries.async_unload(entry.entry_id)
    assert ws_auth.process_success_login is original


async def test_session_wrapper_never_breaks_auth() -> None:
    original = MagicMock()
    hooks = MagicMock()
    hooks.hook_session_opened.side_effect = RuntimeError("bug")
    wrapper = ha_hook.make_session_wrapper(original, hooks)
    request = MagicMock()
    wrapper(request)
    original.assert_called_once_with(request)
    hooks.hook_error.assert_called_once()


async def test_ws_auth_unusable(hass: HomeAssistant) -> None:
    await setup_deps(hass)
    with patch.object(ha_hook, "_ws_auth_module", return_value=None):
        entry = MockConfigEntry(domain=DOMAIN, data={}, options={})
        entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(entry.entry_id)
    manager: BanGuardManager = entry.runtime_data
    assert manager.hook_status == "active"
    assert manager.status()["session_closing"] is False


def test_ws_auth_module_detection() -> None:
    assert ha_hook._ws_auth_module() is ws_auth
    with patch.object(ha_hook, "_source_contains", return_value=False):
        assert ha_hook._ws_auth_module() is None
    with patch.object(ws_auth, "process_success_login", None):
        assert ha_hook._ws_auth_module() is None
    import builtins

    real_import = builtins.__import__

    def failing_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "homeassistant.components.websocket_api":
            raise ImportError(name)
        return real_import(name, *args, **kwargs)

    with patch.object(builtins, "__import__", failing_import):
        assert ha_hook._ws_auth_module() is None


async def test_open_websocket_cut_end_to_end(
    hass: HomeAssistant,
    manager: BanGuardManager,
    hass_client_no_auth: ClientSessionGenerator,
    hass_access_token: str,
) -> None:
    """A real session from a forwarded client address is dropped when it is banned."""
    client = await hass_client_no_auth()
    headers = {"X-Forwarded-For": IP}
    ws = await client.ws_connect("/api/websocket", headers=headers)
    assert (await ws.receive_json())["type"] == "auth_required"
    await ws.send_json({"type": "auth", "access_token": hass_access_token})
    assert (await ws.receive_json())["type"] == "auth_ok"

    await manager.async_ban(IP, source=SOURCE_MANUAL, user=None)

    msg = await ws.receive(timeout=5)
    assert msg.type in (aiohttp.WSMsgType.CLOSE, aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR)
    # Reconnecting is refused by the ban.
    with pytest.raises(aiohttp.WSServerHandshakeError) as err:
        await client.ws_connect("/api/websocket", headers=headers)
    assert err.value.status == 403
