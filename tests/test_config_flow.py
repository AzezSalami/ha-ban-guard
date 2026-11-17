"""Config flow and options flow."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ban_guard.const import CONF_NPM_SECRET, DOMAIN
from custom_components.ban_guard.npm import NPMError
from custom_components.ban_guard.secret import SecretBox
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType


async def test_user_flow(hass: HomeAssistant, http: None) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"protection_enabled": False}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["options"] == {"protection_enabled": False}

    again = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert again["type"] is FlowResultType.ABORT


async def _menu(hass: HomeAssistant, entry: MockConfigEntry, step: str) -> dict[str, Any]:
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.MENU
    return await hass.config_entries.options.async_configure(  # type: ignore[no-any-return]
        result["flow_id"], {"next_step_id": step}
    )


async def test_options_protection(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    result = await _menu(hass, entry, "protection")
    base = {
        "protection_enabled": True,
        "threshold": 3.0,
        "window_minutes": 10.0,
        "escalation": "1h, permanent, 24h",
        "repeated_failures_threshold": 2.0,
        "attack_threshold": 50.0,
        "attack_window_minutes": 5.0,
    }
    result = await hass.config_entries.options.async_configure(result["flow_id"], base)
    assert result["errors"] == {"base": "invalid_escalation"}
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {**base, "escalation": "1h", "network_overrides": "bad line"}
    )
    assert result["errors"] == {"base": "invalid_override"}
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {**base, "escalation": "2h, 1d, permanent", "network_overrides": "10.0.0.0/8: off"},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert entry.options["threshold"] == 3
    assert entry.runtime_data.protection.ladder[0].total_seconds() == 7200


@pytest.mark.parametrize(
    ("step", "data"),
    [
        ("notifications", {"notify_persistent": False, "notify_allowlisted_failures": False}),
        (
            "logging",
            {
                "log_retention_days": 7.0,
                "log_max_entries": 500.0,
                "log_blocked_requests": False,
                "allowlist_refresh_minutes": 60.0,
            },
        ),
    ],
)
async def test_options_simple_steps(
    hass: HomeAssistant, entry: MockConfigEntry, step: str, data: dict[str, Any]
) -> None:
    result = await _menu(hass, entry, step)
    result = await hass.config_entries.options.async_configure(result["flow_id"], data)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    for key, value in data.items():
        assert entry.options[key] == value


async def test_options_enrichment_and_countries(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    result = await _menu(hass, entry, "countries")
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"country_deny": "RU"}
    )
    assert result["errors"] == {"base": "geoip_required"}

    result = await _menu(hass, entry, "enrichment")
    data = {
        "geoip_enabled": True,
        "geoip_edition": "country",
        "geoip_max_mb": 50.0,
        "rdns_enabled": True,
        "doh_enabled": True,
        "doh_url": "http://insecure.example/dns",
    }
    result = await hass.config_entries.options.async_configure(result["flow_id"], data)
    assert result["errors"] == {"doh_url": "invalid_doh_url"}
    with patch("custom_components.ban_guard.manager.GeoIP.async_load", AsyncMock()):
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {**data, "doh_url": "https://dns.example/dns-query"}
        )
        assert result["type"] is FlowResultType.CREATE_ENTRY
        await hass.async_block_till_done()

        result = await _menu(hass, entry, "countries")
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"country_allow": "de", "country_deny": "DE"}
        )
        assert result["errors"] == {"base": "country_conflict"}
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"country_allow": "de, at", "country_deny": ""}
        )
        assert result["type"] is FlowResultType.CREATE_ENTRY
        await hass.async_block_till_done()
    assert entry.options.get("country_allow") == "AT, DE"
    assert entry.options["geoip_max_mb"] == 50


async def test_options_countries_invalid(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    result = await _menu(hass, entry, "countries")
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"country_allow": "Germany"}
    )
    assert result["errors"] == {"base": "invalid_country"}


NPM_INPUT = {
    "npm_enabled": True,
    "npm_url": "http://npm.local:81",
    "npm_username": "admin@example.com",
    "npm_password": "s3cret",
    "npm_verify_ssl": True,
}


async def test_options_npm(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    lists = AsyncMock(return_value=[{"id": 4, "name": "Ban Guard"}])
    with (
        patch("custom_components.ban_guard.config_flow.NPMClient.async_access_lists", lists),
        patch(
            "custom_components.ban_guard.config_flow.async_detect_addon",
            AsyncMock(return_value={"name": "NPM", "suggested_url": "http://a0d7b954-npm:81"}),
        ),
        patch("custom_components.ban_guard.manager.BanGuardManager.async_npm_sync", AsyncMock()),
    ):
        result = await _menu(hass, entry, "npm")
        assert result["description_placeholders"] == {"addon": "NPM"}
        result = await hass.config_entries.options.async_configure(result["flow_id"], NPM_INPUT)
        assert result["step_id"] == "npm_list"
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"npm_access_list_id": "4"}
        )
        assert result["type"] is FlowResultType.CREATE_ENTRY
        await hass.async_block_till_done()
    assert "npm_password" not in entry.options
    secret = entry.options[CONF_NPM_SECRET]
    assert "s3cret" not in secret
    assert await SecretBox(hass).async_decrypt(secret) == "s3cret"
    assert entry.options["npm_access_list_id"] == 4

    # Re-entering without a password keeps the stored one.
    with (
        patch(
            "custom_components.ban_guard.config_flow.NPMClient.async_access_lists",
            AsyncMock(return_value=[{"id": 4, "name": "x"}]),
        ) as lists2,
        patch("custom_components.ban_guard.manager.BanGuardManager.async_npm_sync", AsyncMock()),
    ):
        result = await _menu(hass, entry, "npm")
        data = {k: v for k, v in NPM_INPUT.items() if k != "npm_password"}
        result = await hass.config_entries.options.async_configure(result["flow_id"], data)
        assert result["step_id"] == "npm_list"
        assert lists2.await_count == 1

    result = await _menu(hass, entry, "npm")
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {**NPM_INPUT, "npm_enabled": False}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options["npm_enabled"] is False


@pytest.mark.parametrize(
    ("side_effect", "error"),
    [(NPMError("invalid_auth"), "invalid_auth"), (None, "no_access_lists")],
)
async def test_options_npm_errors(
    hass: HomeAssistant, entry: MockConfigEntry, side_effect: Exception | None, error: str
) -> None:
    lists = AsyncMock(return_value=[], side_effect=side_effect)
    with patch("custom_components.ban_guard.config_flow.NPMClient.async_access_lists", lists):
        result = await _menu(hass, entry, "npm")
        result = await hass.config_entries.options.async_configure(result["flow_id"], NPM_INPUT)
    assert result["errors"] == {"base": error}
