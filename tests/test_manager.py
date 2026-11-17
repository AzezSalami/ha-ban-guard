"""Core manager behaviour: bans, CIDR, expiry, lockout guard, thresholds."""

from __future__ import annotations

from datetime import timedelta
import ipaddress
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

from freezegun.api import FrozenDateTimeFactory
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_capture_events,
    async_fire_time_changed,
)

from custom_components.ban_guard import bansfile
from custom_components.ban_guard.const import (
    ACT_ALLOWLISTED_FAILURE,
    ACT_BAN,
    ACT_BLOCKED,
    ACT_EXPIRED,
    ACT_FAILED_LOGIN,
    ACT_REFUSED,
    EVENT_BAN_GUARD,
    SOURCE_AUTOMATIC,
    SOURCE_HOME_ASSISTANT,
    SOURCE_MANUAL,
)
from custom_components.ban_guard.manager import BanGuardError, BanGuardManager
from homeassistant.components.http import ban as ha_ban
from homeassistant.core import HomeAssistant
from homeassistant.helpers.http import current_request
from homeassistant.util import dt as dt_util

ATTACKER = "203.0.113.7"


def addr(text: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address:
    return ipaddress.ip_address(text)


def lookup(hass: HomeAssistant) -> Any:
    return hass.http.app[ha_ban.KEY_BAN_MANAGER].ip_bans_lookup


def counter(hass: HomeAssistant) -> Any:
    return hass.http.app[ha_ban.KEY_FAILED_LOGIN_ATTEMPTS]


def bans_yaml(hass: HomeAssistant) -> dict[str, Any]:
    return bansfile.read_bans(hass.config.path("ip_bans.yaml"))


async def fail(hass: HomeAssistant, ip: str, times: int = 1) -> None:
    for _ in range(times):
        counter(hass)[addr(ip)] += 1
    # Automatic bans (and their ip_bans.yaml write) run as background tasks.
    await hass.async_block_till_done(wait_background_tasks=True)


async def test_ban_unban_round_trip(hass: HomeAssistant, manager: BanGuardManager) -> None:
    events = async_capture_events(hass, EVENT_BAN_GUARD)
    ban = await manager.async_ban(ATTACKER, reason="scan", source=SOURCE_MANUAL, user=None)
    assert ban.key == ATTACKER and ban.permanent
    assert addr(ATTACKER) in lookup(hass)
    assert ATTACKER in await hass.async_add_executor_job(bans_yaml, hass)
    assert manager.last_ban is not None and manager.last_ban["ip"] == ATTACKER

    await manager.async_unban([ATTACKER], user=None)
    assert addr(ATTACKER) not in lookup(hass)
    assert ATTACKER not in await hass.async_add_executor_job(bans_yaml, hass)
    assert [e.data["type"] for e in events] == ["ban", "unban"]

    with pytest.raises(BanGuardError) as err:
        await manager.async_unban([ATTACKER], user=None)
    assert err.value.key == "not_banned"
    assert "not_banned" in str(err.value)


async def test_cidr_and_ipv6(hass: HomeAssistant, manager: BanGuardManager) -> None:
    await manager.async_ban("198.51.100.0/24", source=SOURCE_MANUAL, user=None)
    await manager.async_ban("2001:db8::/32", source=SOURCE_MANUAL, user=None)
    table = lookup(hass)
    assert addr("198.51.100.77") in table
    assert addr("198.51.101.1") not in table
    assert addr("2001:db8:1::5") in table
    assert addr("::ffff:198.51.100.9") in table  # IPv4-mapped
    assert addr("2001:db9::1") not in table
    # CIDR bans are not written to ip_bans.yaml (HA cannot read them).
    assert await hass.async_add_executor_job(bans_yaml, hass) == {}
    assert bool(table)
    view = manager.ban_view(manager.bans["198.51.100.0/24"])
    assert view["single"] is False and view["in_ip_bans_yaml"] is False


async def test_invalid_targets(manager: BanGuardManager) -> None:
    for bad in ("nope", "10.0.0.1/8", "300.1.1.1"):
        with pytest.raises(BanGuardError) as err:
            await manager.async_ban(bad, source=SOURCE_MANUAL, user=None)
        assert err.value.key == "invalid_ip"
    with pytest.raises(BanGuardError):
        await manager.async_ban(ATTACKER, source="bogus", user=None)
    with pytest.raises(BanGuardError) as err:
        await manager.async_ban(
            ATTACKER,
            source=SOURCE_MANUAL,
            user=None,
            expires_at=dt_util.utcnow() - timedelta(minutes=1),
        )
    assert err.value.key == "expiry_in_past"
    with pytest.raises(BanGuardError):
        await manager.async_unban(["garbage"], user=None)


@pytest.mark.parametrize(
    ("target", "reason"),
    [
        ("127.0.0.1", "protected_loopback"),
        ("127.0.0.0/8", "protected_loopback"),
        ("::1", "protected_loopback"),
        ("192.168.1.10", "protected_host"),
        ("192.168.0.0/16", "protected_host"),
        ("0.0.0.0/0", "protected_loopback"),
    ],
)
async def test_lockout_guard(manager: BanGuardManager, target: str, reason: str) -> None:
    with pytest.raises(BanGuardError) as err:
        await manager.async_ban(target, source=SOURCE_MANUAL, user=None)
    assert err.value.key == reason
    assert not manager.bans


async def test_requester_and_admin_protected(
    hass: HomeAssistant, manager: BanGuardManager, hass_admin_user: Any
) -> None:
    with pytest.raises(BanGuardError) as err:
        await manager.async_ban(
            "198.51.100.0/24", source=SOURCE_MANUAL, user=None, requester=addr("198.51.100.4")
        )
    assert err.value.key == "protected_current"

    token = await hass.auth.async_create_refresh_token(hass_admin_user, "client")
    token.last_used_ip = "198.51.100.200"
    token.last_used_at = dt_util.utcnow()
    await manager.guard.async_refresh_admins()
    with pytest.raises(BanGuardError) as err:
        await manager.async_ban("198.51.100.200", source=SOURCE_MANUAL, user=None)
    assert err.value.key == "protected_admin"


async def test_supervisor_network_protected(hass: HomeAssistant, manager: BanGuardManager) -> None:
    hass.config.components.add("hassio")
    await manager.guard.async_refresh()
    with pytest.raises(BanGuardError) as err:
        await manager.async_ban("172.30.32.5", source=SOURCE_MANUAL, user=None)
    assert err.value.key == "protected_supervisor"


async def test_expiry_lifts_ban(
    hass: HomeAssistant, manager: BanGuardManager, freezer: FrozenDateTimeFactory
) -> None:
    await manager.async_ban(ATTACKER, source=SOURCE_MANUAL, user=None, duration=timedelta(hours=1))
    assert addr(ATTACKER) in lookup(hass)
    # Temporary bans are not mirrored to ip_bans.yaml.
    assert await hass.async_add_executor_job(bans_yaml, hass) == {}
    freezer.tick(timedelta(hours=1, seconds=1))
    # Expired bans stop blocking immediately, even before the purge runs.
    assert addr(ATTACKER) not in lookup(hass)
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert ATTACKER not in manager.bans
    assert manager.activity.entries(types={ACT_EXPIRED})[0].ip == ATTACKER
    assert await manager.async_purge_expired() == 0


async def test_rebanning_temporary_moves_out_of_yaml(
    hass: HomeAssistant, manager: BanGuardManager
) -> None:
    await manager.async_ban(ATTACKER, source=SOURCE_MANUAL, user=None)
    assert ATTACKER in await hass.async_add_executor_job(bans_yaml, hass)
    await manager.async_ban(ATTACKER, source=SOURCE_MANUAL, user=None, duration=timedelta(hours=2))
    assert ATTACKER not in await hass.async_add_executor_job(bans_yaml, hass)
    assert addr(ATTACKER) in lookup(hass)


async def test_threshold_and_escalation(
    hass: HomeAssistant, manager: BanGuardManager, freezer: FrozenDateTimeFactory
) -> None:
    events = async_capture_events(hass, EVENT_BAN_GUARD)
    # HA's own threshold is delegated to Ban Guard.
    assert hass.http.app[ha_ban.KEY_LOGIN_THRESHOLD] > 1000
    await fail(hass, ATTACKER, 4)
    assert ATTACKER not in manager.bans
    assert "repeated_failures" in [e.data["type"] for e in events]
    await fail(hass, ATTACKER, 1)
    ban = manager.bans[ATTACKER]
    assert ban.source == SOURCE_AUTOMATIC and ban.offense == 1
    assert ban.expires_at is not None
    assert ban.expires_at - ban.created_at == timedelta(hours=1)

    freezer.tick(timedelta(hours=2))
    await manager.async_purge_expired()
    await fail(hass, ATTACKER, 5)
    second = manager.bans[ATTACKER]
    assert second.offense == 2
    assert second.expires_at is not None
    assert second.expires_at - second.created_at == timedelta(hours=24)

    freezer.tick(timedelta(days=2))
    await manager.async_purge_expired()
    await fail(hass, ATTACKER, 5)
    assert manager.bans[ATTACKER].permanent
    assert ATTACKER in await hass.async_add_executor_job(bans_yaml, hass)


async def test_failures_outside_window_do_not_count(
    hass: HomeAssistant, manager: BanGuardManager, freezer: FrozenDateTimeFactory
) -> None:
    await fail(hass, ATTACKER, 4)
    freezer.tick(timedelta(minutes=16))
    await fail(hass, ATTACKER, 4)
    assert ATTACKER not in manager.bans
    assert manager.activity.count_since(ACT_FAILED_LOGIN, dt_util.utcnow() - timedelta(days=1)) == 8


async def test_offense_decays(
    hass: HomeAssistant, manager: BanGuardManager, freezer: FrozenDateTimeFactory
) -> None:
    await fail(hass, ATTACKER, 5)
    freezer.tick(timedelta(days=31))
    await manager.async_purge_expired()
    await fail(hass, ATTACKER, 5)
    assert manager.bans[ATTACKER].offense == 1


@pytest.mark.parametrize(
    "options",
    [{"network_overrides": "203.0.113.0/24: 2/5\n10.0.0.0/8: off", "escalation": "30m"}],
)
async def test_network_overrides(hass: HomeAssistant, manager: BanGuardManager) -> None:
    await fail(hass, ATTACKER, 2)
    ban = manager.bans[ATTACKER]
    assert ban.expires_at is not None
    assert ban.expires_at - ban.created_at == timedelta(minutes=30)
    await fail(hass, "10.1.2.3", 50)
    assert "10.1.2.3" not in manager.bans


async def test_protected_address_never_auto_banned(
    hass: HomeAssistant, manager: BanGuardManager
) -> None:
    await fail(hass, "192.168.1.10", 5)
    assert not manager.bans
    assert manager.activity.entries(types={ACT_REFUSED})


async def test_allowlist(hass: HomeAssistant, manager: BanGuardManager) -> None:
    events = async_capture_events(hass, EVENT_BAN_GUARD)
    await manager.async_allow("203.0.113.0/24", comment="office", user=None)
    with pytest.raises(BanGuardError) as err:
        await manager.async_ban(ATTACKER, source=SOURCE_MANUAL, user=None)
    assert err.value.key == "allowlisted"
    # A wider ban still never blocks the allowlisted part.
    await manager.async_ban("203.0.0.0/16", source=SOURCE_MANUAL, user=None)
    assert addr(ATTACKER) not in lookup(hass)
    assert addr("203.0.200.1") in lookup(hass)

    await fail(hass, ATTACKER, 10)
    assert ATTACKER not in manager.bans
    assert manager.activity.entries(types={ACT_ALLOWLISTED_FAILURE})
    assert "allowlisted_failure" in [e.data["type"] for e in events]

    with pytest.raises(BanGuardError):
        await manager.async_allow("not a host!", user=None)
    await manager.async_disallow("203.0.113.0/24", user=None)
    with pytest.raises(BanGuardError):
        await manager.async_disallow("203.0.113.0/24", user=None)
    assert addr(ATTACKER) in lookup(hass)


async def test_allowlist_hostname(hass: HomeAssistant, manager: BanGuardManager) -> None:
    manager.resolver.async_resolve = MagicMock()  # type: ignore[method-assign]

    async def resolve(name: str) -> list[str]:
        return ["198.51.100.20"]

    manager.resolver.async_resolve = resolve  # type: ignore[method-assign]
    entry = await manager.async_allow("Home.Example.org", user=None)
    assert entry.value == "home.example.org" and entry.resolved == ["198.51.100.20"]
    assert manager.is_allowlisted(addr("198.51.100.20"))

    async def resolve2(name: str) -> list[str]:
        return ["198.51.100.21"]

    manager.resolver.async_resolve = resolve2  # type: ignore[method-assign]
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=31))
    await hass.async_block_till_done()
    assert manager.is_allowlisted(addr("198.51.100.21"))
    assert not manager.is_allowlisted(addr("198.51.100.20"))


async def test_blocked_requests_logged_once_per_minute(
    hass: HomeAssistant, manager: BanGuardManager
) -> None:
    await manager.async_ban(ATTACKER, source=SOURCE_MANUAL, user=None)
    request = MagicMock()
    request.path = "/api/webhook/abcdefghijklmnopqrstuvwxyz0123"
    request.headers = {"User-Agent": "curl/8"}
    token = current_request.set(request)
    try:
        for _ in range(5):
            assert addr(ATTACKER) in lookup(hass)
    finally:
        current_request.reset(token)
    blocked = manager.activity.entries(types={ACT_BLOCKED})
    assert len(blocked) == 1
    assert blocked[0].path == "/api/webhook/<redacted>"
    assert blocked[0].user_agent == "curl/8"


@pytest.mark.parametrize("options", [{"log_blocked_requests": False}])
async def test_blocked_logging_off(hass: HomeAssistant, manager: BanGuardManager) -> None:
    await manager.async_ban(ATTACKER, source=SOURCE_MANUAL, user=None)
    assert addr(ATTACKER) in lookup(hass)
    assert not manager.activity.entries(types={ACT_BLOCKED})


async def test_ha_own_ban_recorded(hass: HomeAssistant, manager: BanGuardManager) -> None:
    ha_manager = hass.http.app[ha_ban.KEY_BAN_MANAGER]
    await ha_manager.async_add_ban(addr("198.51.100.50"))
    await hass.async_block_till_done()
    assert manager.bans["198.51.100.50"].source == SOURCE_HOME_ASSISTANT
    # HA tries to ban an allowlisted address: reverted.
    await manager.async_allow("198.51.100.60", user=None)
    await ha_manager.async_add_ban(addr("198.51.100.60"))
    assert addr("198.51.100.60") not in lookup(hass)
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=3))
    await hass.async_block_till_done(wait_background_tasks=True)
    assert "198.51.100.60" not in manager.bans
    assert "198.51.100.60" not in await hass.async_add_executor_job(bans_yaml, hass)


async def test_reconcile_with_existing_yaml(hass: HomeAssistant, http: None) -> None:
    path = Path(hass.config.path("ip_bans.yaml"))
    await hass.async_add_executor_job(
        path.write_text,
        "198.51.100.1:\n  banned_at: '2026-01-01T00:00:00+00:00'\nnot-an-ip:\n  banned_at: null\n",
    )
    entry = MockConfigEntry(domain="ban_guard", data={}, options={})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    manager: BanGuardManager = entry.runtime_data
    assert manager.bans["198.51.100.1"].source == SOURCE_HOME_ASSISTANT
    assert addr("198.51.100.1") in lookup(hass)
    await manager.async_ban("198.51.100.2", source=SOURCE_MANUAL, user=None)
    text = await hass.async_add_executor_job(path.read_text)
    assert "not-an-ip" in text  # unknown entries preserved
    assert "198.51.100.2" in text

    # Removing a permanent ban from the file by hand is honoured on reload.
    await hass.async_add_executor_job(bansfile.update_bans, str(path), {}, ["198.51.100.1"])
    await hass.config_entries.async_reload(entry.entry_id)
    manager = entry.runtime_data
    assert "198.51.100.1" not in manager.bans
    assert "198.51.100.2" in manager.bans


async def test_persistence_across_reload(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    manager: BanGuardManager = entry.runtime_data
    await manager.async_ban(
        "198.51.100.0/24", reason="r", source=SOURCE_MANUAL, user=None, duration=timedelta(days=1)
    )
    await manager.async_allow("10.0.0.0/8", comment="lan", user=None)
    await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    manager = entry.runtime_data
    assert "198.51.100.0/24" in manager.bans
    assert "10.0.0.0/8" in manager.allow
    assert manager.activity.entries(types={ACT_BAN})


async def test_restore_undo(hass: HomeAssistant, manager: BanGuardManager) -> None:
    await manager.async_ban(ATTACKER, source=SOURCE_MANUAL, user=None)
    removed = await manager.async_unban([ATTACKER], user=None)
    await manager.async_restore([b.as_dict() for b in removed])
    assert addr(ATTACKER) in lookup(hass)


async def test_under_attack(hass: HomeAssistant, manager: BanGuardManager) -> None:
    assert not manager.is_under_attack()
    for i in range(20):
        await fail(hass, f"198.51.100.{i}", 1)
    assert manager.is_under_attack()
    assert manager.recent_failure_count() == 20


@pytest.mark.parametrize("options", [{"protection_enabled": False}])
async def test_protection_disabled(hass: HomeAssistant, manager: BanGuardManager) -> None:
    assert hass.http.app[ha_ban.KEY_LOGIN_THRESHOLD] == 5
    await fail(hass, ATTACKER, 4)
    assert ATTACKER not in manager.bans
    assert (
        manager.activity.count_since(ACT_FAILED_LOGIN, dt_util.utcnow() - timedelta(hours=1)) == 4
    )


async def test_user_names_recorded(
    hass: HomeAssistant, manager: BanGuardManager, hass_admin_user: Any
) -> None:
    ban = await manager.async_ban(ATTACKER, source=SOURCE_MANUAL, user=hass_admin_user.id)
    assert ban.created_by == hass_admin_user.name
    ban = await manager.async_ban("198.51.100.3", source=SOURCE_MANUAL, user="missing-user")
    assert ban.created_by == "missing-user"


async def test_history(manager: BanGuardManager) -> None:
    await manager.async_ban(ATTACKER, reason="x", source=SOURCE_MANUAL, user=None)
    history = await manager.async_history(ATTACKER)
    assert history["ban"]["ip"] == ATTACKER
    assert history["activity"][0]["type"] == "ban"
    assert history["hostname"] is None
    assert history["allowlisted"] is False
    with pytest.raises(BanGuardError):
        await manager.async_history("bad")
    net = await manager.async_history("198.51.100.0/24")
    assert net["ban"] is None


async def test_status(manager: BanGuardManager) -> None:
    status = manager.status()
    assert status["hook"] == "active"
    assert status["ha_login_threshold"] == 5
    assert status["geoip"]["enabled"] is False


async def test_unload_restores_ha(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    assert await hass.config_entries.async_unload(entry.entry_id)
    table = lookup(hass)
    assert type(table) is dict
    assert type(counter(hass)).__name__ == "defaultdict"
    assert hass.http.app[ha_ban.KEY_LOGIN_THRESHOLD] == 5
