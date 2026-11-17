"""Setup, unload, removal and panel registration."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ban_guard import panel
from custom_components.ban_guard.const import DOMAIN, PANEL_URL_PATH
from custom_components.ban_guard.manager import BanGuardManager
from homeassistant.components import frontend
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant


async def test_unload_and_remove(
    hass: HomeAssistant, entry: MockConfigEntry, hass_storage: dict
) -> None:
    manager: BanGuardManager = entry.runtime_data
    await manager.async_ban("198.51.100.1", source="manual", user=None)
    await manager.secret.async_encrypt("x")
    assert await hass.config_entries.async_unload(entry.entry_id)
    assert entry.state is ConfigEntryState.NOT_LOADED
    assert "ban_guard.data" in hass_storage
    await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()
    assert "ban_guard.data" not in hass_storage
    assert "ban_guard.secret" not in hass_storage


async def test_options_update_reloads(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    first = entry.runtime_data
    hass.config_entries.async_update_entry(entry, options={"threshold": 7})
    await hass.async_block_till_done()
    assert entry.runtime_data is not first
    assert entry.runtime_data.protection.threshold == 7


async def test_invalid_stored_options_fall_back(hass: HomeAssistant, http: None) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={},
        options={"escalation": "nonsense", "country_deny": "XYZ"},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    manager: BanGuardManager = entry.runtime_data
    assert manager.protection.threshold == 5
    assert manager.country_deny == frozenset()


async def test_corrupt_storage_is_skipped(
    hass: HomeAssistant, http: None, hass_storage: dict
) -> None:
    hass_storage["ban_guard.data"] = {
        "version": 1,
        "key": "ban_guard.data",
        "data": {
            "bans": [{"ip": "bad"}, {"ip": "198.51.100.1", "expires_at": "2999-01-01T00:00:00Z"}],
            "allowlist": [{"nope": 1}, {"value": "10.0.0.0/8"}],
            "offenses": {
                "1.2.3.4": {"bad": 1},
                "5.6.7.8": {"count": 2, "last": "2026-01-01T00:00:00Z"},
            },
        },
    }
    hass_storage["ban_guard.activity"] = {
        "version": 1,
        "key": "ban_guard.activity",
        "data": {
            "entries": [
                {"id": "x"},
                {"id": 1, "ts": "2999-01-01T00:00:00Z", "type": "ban", "ip": "1.1.1.1"},
            ]
        },
    }
    entry = MockConfigEntry(domain=DOMAIN, data={}, options={})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    manager: BanGuardManager = entry.runtime_data
    assert list(manager.bans) == ["198.51.100.1"]
    assert list(manager.allow) == ["10.0.0.0/8"]
    assert list(manager.offenses) == ["5.6.7.8"]
    assert len(manager.activity) == 1


async def test_panel_registration(hass: HomeAssistant) -> None:
    hass.http = MagicMock()
    hass.http.async_register_static_paths = AsyncMock()
    hass.data[frontend.DATA_PANELS] = {}
    with patch.object(panel.panel_custom, "async_register_panel", AsyncMock()) as register:
        await panel.async_register_panel(hass)
        hass.data[frontend.DATA_PANELS][PANEL_URL_PATH] = object()
        await panel.async_register_panel(hass)
    assert register.await_count == 1
    kwargs = register.await_args.kwargs
    assert kwargs["require_admin"] is True
    assert kwargs["module_url"].startswith("/ban_guard_static/ban-guard-panel.js?v=")
    assert hass.http.async_register_static_paths.await_count == 1
    static = hass.http.async_register_static_paths.await_args.args[0][0]
    assert static.path.endswith("ban-guard-panel.js")
    with patch.object(frontend, "async_remove_panel") as remove:
        panel.async_unregister_panel(hass)
        remove.assert_called_once_with(hass, PANEL_URL_PATH)
        hass.data[frontend.DATA_PANELS].clear()
        panel.async_unregister_panel(hass)
        assert remove.call_count == 1
