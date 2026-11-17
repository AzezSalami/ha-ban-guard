"""Services, admin enforcement, import/export, entities and diagnostics."""

from __future__ import annotations

from datetime import timedelta
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.components.diagnostics import (
    get_diagnostics_for_config_entry,
)
from pytest_homeassistant_custom_component.typing import ClientSessionGenerator

from custom_components.ban_guard.const import DOMAIN, SOURCE_MANUAL, SOURCE_SERVICE
from custom_components.ban_guard.manager import BanGuardError, BanGuardManager
from homeassistant.core import Context, HomeAssistant
from homeassistant.exceptions import ServiceValidationError, Unauthorized
from homeassistant.util import dt as dt_util


async def test_services_round_trip(
    hass: HomeAssistant, manager: BanGuardManager, hass_admin_user: Any
) -> None:
    ctx = Context(user_id=hass_admin_user.id)
    await hass.services.async_call(
        DOMAIN,
        "ban",
        {"ip": "198.51.100.1", "duration": "1d", "reason": "r"},
        blocking=True,
        context=ctx,
    )
    ban = manager.bans["198.51.100.1"]
    assert ban.source == SOURCE_SERVICE and ban.created_by == hass_admin_user.name
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN, "ban", {"ip": "198.51.100.2", "duration": "later"}, blocking=True
        )
    with pytest.raises(BanGuardError):
        await hass.services.async_call(DOMAIN, "ban", {"ip": "::1"}, blocking=True)
    await hass.services.async_call(DOMAIN, "unban", {"ip": "198.51.100.1"}, blocking=True)
    assert not manager.bans

    await hass.services.async_call(
        DOMAIN, "allow", {"value": "10.0.0.0/8", "comment": "lan"}, blocking=True
    )
    assert "10.0.0.0/8" in manager.allow
    await hass.services.async_call(DOMAIN, "disallow", {"value": "10.0.0.0/8"}, blocking=True)
    assert not manager.allow

    await manager.async_ban(
        "198.51.100.3", source=SOURCE_MANUAL, user=None, duration=timedelta(hours=1)
    )
    manager.bans["198.51.100.3"].expires_at = dt_util.utcnow() - timedelta(seconds=1)
    result = await hass.services.async_call(
        DOMAIN, "purge_expired", {}, blocking=True, return_response=True
    )
    assert result == {"lifted": 1}

    await manager.async_ban("198.51.100.4", source=SOURCE_MANUAL, user=None)
    backup = await hass.services.async_call(
        DOMAIN, "export", {}, blocking=True, return_response=True
    )
    assert backup is not None and backup["bans"][0]["ip"] == "198.51.100.4"
    backup["bans"].append({"ip": "198.51.100.5", "reason": "imp"})
    backup["allowlist"].append({"value": "home.example.com"})
    backup["settings"] = {"threshold": 9}
    preview = await hass.services.async_call(
        DOMAIN, "import", {"data": backup}, blocking=True, return_response=True
    )
    assert preview is not None and preview["dry_run"] is True
    assert "198.51.100.5" not in manager.bans
    with patch.object(manager.resolver, "async_resolve", AsyncMock(return_value=[])):
        applied = await hass.services.async_call(
            DOMAIN,
            "import",
            {"data": backup, "dry_run": False, "include_settings": True},
            blocking=True,
            return_response=True,
        )
    assert applied is not None and applied["dry_run"] is False
    await hass.async_block_till_done()
    assert hass.config_entries.async_entries(DOMAIN)[0].options["threshold"] == 9


async def test_services_require_admin(
    hass: HomeAssistant, manager: BanGuardManager, hass_read_only_user: Any
) -> None:
    ctx = Context(user_id=hass_read_only_user.id)
    for service, data in (
        ("ban", {"ip": "198.51.100.1"}),
        ("unban", {"ip": "198.51.100.1"}),
        ("allow", {"value": "198.51.100.1"}),
        ("disallow", {"value": "198.51.100.1"}),
        ("purge_expired", {}),
    ):
        with pytest.raises(Unauthorized):
            await hass.services.async_call(DOMAIN, service, data, blocking=True, context=ctx)
    assert not manager.bans


async def test_service_without_entry(hass: HomeAssistant) -> None:
    from homeassistant.setup import async_setup_component

    from .conftest import setup_deps

    await setup_deps(hass)
    assert await async_setup_component(hass, DOMAIN, {})
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(DOMAIN, "unban", {"ip": "1.2.3.4"}, blocking=True)


async def test_import_validation(manager: BanGuardManager) -> None:
    for bad in ([], {"format": "nope"}, {"format": "ban_guard", "version": 99}):
        with pytest.raises(BanGuardError):
            manager.validate_import(bad)
    with pytest.raises(BanGuardError):
        manager.validate_import({"format": "ban_guard", "bans": "x"})
    with pytest.raises(BanGuardError):
        manager.validate_import({"format": "ban_guard", "settings": "x"})
    with (
        patch("custom_components.ban_guard.manager.MAX_IMPORT_ITEMS", 1),
        pytest.raises(BanGuardError),
    ):
        manager.validate_import({"format": "ban_guard", "bans": [{}, {}]})

    preview = manager.validate_import(
        {
            "format": "ban_guard",
            "version": 1,
            "bans": [
                {"ip": "198.51.100.1"},
                {"ip": "127.0.0.1"},
                {"ip": "garbage"},
                "not-a-dict",
                {"ip": "198.51.100.2", "expires_at": "2000-01-01T00:00:00Z"},
                {"ip": "198.51.100.3", "expires_at": "yesterday-ish"},
            ],
            "allowlist": [{"value": "10.0.0.0/8"}, {"value": "!!"}, "x"],
            "settings": {"threshold": 0, "unknown": 1},
        }
    )
    assert [b["ip"] for b in preview["bans_new"]] == ["198.51.100.1"]
    assert preview["bans_expired"] == ["198.51.100.2"]
    errors = {(e["section"], e["error"]) for e in preview["errors"]}
    assert ("bans", "protected_loopback") in errors
    assert ("bans", "invalid") in errors
    assert ("allowlist", "invalid_allow") in errors
    assert ("settings", "invalid_threshold") in errors
    assert preview["settings"] == {}
    assert preview["allow_new"] == [{"value": "10.0.0.0/8", "comment": ""}]


async def test_entities(hass: HomeAssistant, manager: BanGuardManager) -> None:
    await manager.async_ban("198.51.100.1", source=SOURCE_MANUAL, user=None, reason="x")
    await manager.async_ban(
        "198.51.100.0/28", source=SOURCE_MANUAL, user=None, duration=timedelta(hours=1)
    )
    await hass.async_block_till_done()
    assert hass.states.get("sensor.ban_guard_active_bans").state == "2"
    attrs = hass.states.get("sensor.ban_guard_active_bans").attributes
    assert attrs["permanent"] == 1 and attrs["networks"] == 1
    assert hass.states.get("sensor.ban_guard_bans_in_the_last_24_hours").state == "2"
    last = hass.states.get("sensor.ban_guard_last_banned_ip")
    assert last.state == "198.51.100.0/28"
    assert last.attributes["source"] == SOURCE_MANUAL
    assert hass.states.get("binary_sensor.ban_guard_under_attack").state == "off"
    assert hass.states.get("binary_sensor.ban_guard_under_attack").attributes["threshold"] == 20


async def test_entities_empty(hass: HomeAssistant, manager: BanGuardManager) -> None:
    state = hass.states.get("sensor.ban_guard_last_banned_ip")
    assert state.state == "unknown"
    assert hass.states.get("sensor.ban_guard_failed_logins_in_the_last_24_hours").state == "0"


async def test_diagnostics_redact_ips(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    hass_client: ClientSessionGenerator,
) -> None:
    manager: BanGuardManager = entry.runtime_data
    await manager.async_ban("198.51.100.77", source=SOURCE_MANUAL, user=None, reason="why")
    await manager.async_allow("vpn.example.com", comment="secret place", user=None)
    manager.activity.add("failed_login", "203.0.113.99", path="/auth", user_agent="ua")
    diag = await get_diagnostics_for_config_entry(hass, hass_client, entry)
    text = str(diag)
    for secret in ("198.51.100.77", "203.0.113.99", "vpn.example.com", "secret place"):
        assert secret not in text
    assert diag["bans"][0]["ip"].startswith("<ip:")
    assert diag["counts"]["bans"] == 1
