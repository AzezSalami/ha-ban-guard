"""Successful-login logging through HA's auth login flow."""

from __future__ import annotations

import ipaddress
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ban_guard import ha_hook
from custom_components.ban_guard.const import ACT_FAILED_LOGIN, ACT_LOGIN, DOMAIN
from custom_components.ban_guard.manager import BanGuardManager
from homeassistant.components.auth import login_flow
from homeassistant.components.http import ban as ha_ban
from homeassistant.core import HomeAssistant
from homeassistant.helpers.http import current_request

from .conftest import setup_deps

IP = "198.51.100.40"


def _request(hass: HomeAssistant, ip: str = IP) -> MagicMock:
    request = MagicMock()
    request.app = hass.http.app
    request.remote = ip
    request.path = "/auth/login_flow/abcdefghijklmnopqrstuvwxyz123456"
    request.headers = {"User-Agent": "Mozilla/5.0 Test"}
    return request


def _login_flow_success(request: Any, user: Any) -> None:
    """Mimic LoginFlowResourceView.post: `user` is a local when it calls the hook."""
    assert user is not None
    login_flow.process_success_login(request)


async def test_successful_login_logged(
    hass: HomeAssistant, manager: BanGuardManager, hass_admin_user: Any
) -> None:
    assert manager.status()["login_logging"] is True
    assert hasattr(login_flow.process_success_login, "__ban_guard_original__")
    request = _request(hass)
    token = current_request.set(request)
    try:
        # A few failures first, then a good login clears them (HA and Ban Guard).
        for _ in range(3):
            hass.http.app[ha_ban.KEY_FAILED_LOGIN_ATTEMPTS][ipaddress.ip_address(IP)] += 1
        await hass.async_block_till_done(wait_background_tasks=True)
        _login_flow_success(request, hass_admin_user)
    finally:
        current_request.reset(token)
    await hass.async_block_till_done()
    entry = manager.activity.entries(types={ACT_LOGIN})[0]
    assert entry.ip == IP
    assert entry.user == hass_admin_user.name
    assert entry.user_agent == "Mozilla/5.0 Test"
    assert entry.path == "/auth/login_flow/<redacted>"
    # HA's original still ran: its failure counter for the address was reset.
    assert ipaddress.ip_address(IP) not in hass.http.app[ha_ban.KEY_FAILED_LOGIN_ATTEMPTS]
    assert ipaddress.ip_address(IP) not in manager._failures
    assert len(manager.activity.entries(types={ACT_FAILED_LOGIN})) == 3
    assert manager.activity.stats(manager.country_of)["logins_24h"] == 1


async def test_login_without_user_local(hass: HomeAssistant, manager: BanGuardManager) -> None:
    login_flow.process_success_login(_request(hass, "::ffff:198.51.100.41"))
    entry = manager.activity.entries(types={ACT_LOGIN})[0]
    assert entry.ip == "198.51.100.41"
    assert entry.user is None


async def test_websocket_reauth_not_logged(hass: HomeAssistant, manager: BanGuardManager) -> None:
    from homeassistant.components.websocket_api import auth as ws_auth

    ws_auth.process_success_login(_request(hass))
    assert not manager.activity.entries(types={ACT_LOGIN})


@pytest.mark.parametrize("options", [{"log_successful_logins": False}])
async def test_option_off(hass: HomeAssistant, manager: BanGuardManager) -> None:
    assert not hasattr(login_flow.process_success_login, "__ban_guard_original__")
    login_flow.process_success_login(_request(hass))
    assert not manager.activity.entries(types={ACT_LOGIN})
    assert manager.status()["login_logging"] is False


async def test_unload_restores_original(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    original = login_flow.process_success_login.__ban_guard_original__
    assert await hass.config_entries.async_unload(entry.entry_id)
    assert login_flow.process_success_login is original


async def test_reload_does_not_double_wrap(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    inner = login_flow.process_success_login.__ban_guard_original__
    assert not hasattr(inner, "__ban_guard_original__")


async def test_wrapper_errors_never_break_login(hass: HomeAssistant, http: None) -> None:
    original = MagicMock()
    hooks = MagicMock()
    hooks.hook_login_success.side_effect = RuntimeError("bug")
    wrapper = ha_hook.make_success_wrapper(original, hooks)
    request = _request(hass)
    wrapper(request)  # must not raise
    original.assert_called_once_with(request)
    hooks.hook_error.assert_called_once()
    # No remote address: nothing reported, original still called.
    request.remote = None
    wrapper(request)
    assert original.call_count == 2
    assert hooks.hook_login_success.call_count == 1


async def test_login_flow_unusable(hass: HomeAssistant) -> None:
    await setup_deps(hass)
    with patch.object(ha_hook, "_login_flow_module", return_value=None):
        entry = MockConfigEntry(domain=DOMAIN, data={}, options={})
        entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(entry.entry_id)
    manager: BanGuardManager = entry.runtime_data
    assert manager.hook_status == "active"  # the rest of the hook still works
    assert manager.status()["login_logging"] is False
    assert manager.hook is not None
    manager.hook.set_login_logging(True)  # no-op without a module


def test_login_flow_module_detection() -> None:
    assert ha_hook._login_flow_module() is login_flow
    with patch.object(ha_hook, "_source_contains", return_value=False):
        assert ha_hook._login_flow_module() is None
    with patch.object(login_flow, "process_success_login", None):
        assert ha_hook._login_flow_module() is None
    import builtins

    real_import = builtins.__import__

    def failing_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "homeassistant.components.auth":
            raise ImportError(name)
        return real_import(name, *args, **kwargs)

    with patch.object(builtins, "__import__", failing_import):
        assert ha_hook._login_flow_module() is None
