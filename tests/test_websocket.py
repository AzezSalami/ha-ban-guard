"""Websocket API, including admin-only permissions."""

from __future__ import annotations

from typing import Any

import pytest
from pytest_homeassistant_custom_component.typing import WebSocketGenerator

from custom_components.ban_guard.const import CONF_NPM_SECRET, SOURCE_MANUAL
from custom_components.ban_guard.manager import BanGuardManager
from custom_components.ban_guard.websocket import ACTIVITY_TYPES
from homeassistant.core import HomeAssistant

COMMANDS: list[dict[str, Any]] = [
    {"type": "ban_guard/overview"},
    {"type": "ban_guard/bans"},
    {"type": "ban_guard/ban", "ip": "198.51.100.1"},
    {"type": "ban_guard/unban", "ips": ["198.51.100.1"]},
    {"type": "ban_guard/restore", "bans": []},
    {"type": "ban_guard/allowlist"},
    {"type": "ban_guard/allow", "value": "198.51.100.2"},
    {"type": "ban_guard/disallow", "value": "198.51.100.2"},
    {"type": "ban_guard/activity"},
    {"type": "ban_guard/subscribe_activity"},
    {"type": "ban_guard/subscribe_updates"},
    {"type": "ban_guard/history", "ip": "198.51.100.1"},
    {"type": "ban_guard/export"},
    {"type": "ban_guard/import", "data": {}},
    {"type": "ban_guard/settings"},
    {"type": "ban_guard/npm_sync"},
]


@pytest.mark.parametrize("command", COMMANDS)
async def test_non_admin_rejected(
    hass: HomeAssistant,
    manager: BanGuardManager,
    hass_ws_client: WebSocketGenerator,
    hass_read_only_access_token: str,
    command: dict[str, Any],
) -> None:
    ws = await hass_ws_client(hass, hass_read_only_access_token)
    await ws.send_json_auto_id(command)
    msg = await ws.receive_json()
    assert not msg["success"]
    assert msg["error"]["code"] == "unauthorized"
    assert not manager.bans


async def test_not_loaded(hass: HomeAssistant, hass_ws_client: WebSocketGenerator) -> None:
    from homeassistant.setup import async_setup_component

    from .conftest import setup_deps

    await setup_deps(hass)
    assert await async_setup_component(hass, "ban_guard", {})
    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id({"type": "ban_guard/bans"})
    msg = await ws.receive_json()
    assert msg["error"]["code"] == "not_loaded"


async def test_full_flow(
    hass: HomeAssistant, manager: BanGuardManager, hass_ws_client: WebSocketGenerator
) -> None:
    ws = await hass_ws_client(hass)

    events: list[dict[str, Any]] = []

    async def call(**data: Any) -> dict[str, Any]:
        await ws.send_json_auto_id(data)
        while True:
            msg = await ws.receive_json()
            if msg["type"] == "event":
                events.append(msg)
                continue
            return msg  # type: ignore[no-any-return]

    sub_activity = await call(type="ban_guard/subscribe_activity")
    assert sub_activity["success"]
    sub_updates = await call(type="ban_guard/subscribe_updates")
    assert sub_updates["success"]

    msg = await call(type="ban_guard/ban", ip="198.51.100.1", reason="r", duration="2h")
    assert msg["success"], msg
    assert msg["result"]["ban"]["expires_at"]
    await call(type="ban_guard/bans")
    ids = {e["id"] for e in events}
    assert sub_activity["id"] in ids and sub_updates["id"] in ids
    assert any(
        e["event"].get("entry", {}).get("type") == "ban"
        for e in events
        if e["id"] == sub_activity["id"]
    )

    msg = await call(type="ban_guard/ban", ip="127.0.0.1")
    assert msg["error"]["code"] == "protected_loopback"
    msg = await call(type="ban_guard/ban", ip="198.51.100.5", duration="soon")
    assert msg["error"]["code"] == "invalid_duration"

    msg = await call(type="ban_guard/bans")
    assert [b["ip"] for b in msg["result"]["bans"]] == ["198.51.100.1"]

    msg = await call(type="ban_guard/history", ip="198.51.100.1")
    assert msg["result"]["ban"]["reason"] == "r"

    msg = await call(type="ban_guard/unban", ips=["198.51.100.1"])
    removed = msg["result"]["removed"]
    assert removed[0]["ip"] == "198.51.100.1"
    msg = await call(type="ban_guard/restore", bans=removed)
    assert msg["success"]
    assert "198.51.100.1" in manager.bans
    msg = await call(type="ban_guard/restore", bans=[{"ip": "127.0.0.1"}])
    assert msg["error"]["code"] == "protected_loopback"
    msg = await call(type="ban_guard/restore", bans=[{"nope": 1}])
    assert msg["error"]["code"] == "invalid_ip"

    msg = await call(type="ban_guard/allow", value="vpn.example.com", comment="vpn")
    assert msg["result"]["entry"]["hostname"] is True
    msg = await call(type="ban_guard/allowlist")
    assert msg["result"]["allowlist"][0]["value"] == "vpn.example.com"
    msg = await call(type="ban_guard/disallow", value="vpn.example.com")
    assert msg["success"]

    msg = await call(type="ban_guard/activity", limit=2, types=ACTIVITY_TYPES)
    assert len(msg["result"]["entries"]) == 2
    before = msg["result"]["entries"][-1]["id"]
    msg = await call(type="ban_guard/activity", before_id=before, ip="198.51.100.1")
    assert all(e["id"] < before for e in msg["result"]["entries"])

    msg = await call(type="ban_guard/overview")
    assert msg["result"]["active_bans"] == 1
    assert len(msg["result"]["failed_logins_7d"]) == 7

    msg = await call(type="ban_guard/settings")
    assert CONF_NPM_SECRET not in msg["result"]["options"]
    assert msg["result"]["requester_ip"] == "127.0.0.1"
    assert msg["result"]["npm_addon"] is None

    msg = await call(type="ban_guard/export")
    backup = msg["result"]
    assert backup["format"] == "ban_guard"
    msg = await call(type="ban_guard/import", data=backup)
    assert msg["result"]["dry_run"] is True
    assert msg["result"]["preview"]["bans_existing"] == ["198.51.100.1"]
    msg = await call(type="ban_guard/import", data={"format": "x"})
    assert msg["error"]["code"] == "import_invalid_format"
    backup["bans"].append({"ip": "198.51.100.77", "created_at": "2026-01-01T00:00:00Z"})
    msg = await call(type="ban_guard/import", data=backup, dry_run=False)
    assert msg["result"]["dry_run"] is False
    assert "198.51.100.77" in manager.bans

    msg = await call(type="ban_guard/npm_sync")
    assert msg["result"] == {"enabled": False}


async def test_overview_with_activity(
    hass: HomeAssistant, manager: BanGuardManager, hass_ws_client: WebSocketGenerator
) -> None:
    await manager.async_ban("198.51.100.0/24", source=SOURCE_MANUAL, user=None)
    manager.activity.add("failed_login", "203.0.113.5")
    manager.activity.add("blocked", "203.0.113.5")
    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id({"type": "ban_guard/overview"})
    result = (await ws.receive_json())["result"]
    assert result["top_ips"][0] == {"ip": "203.0.113.5", "count": 2}
    assert result["failed_logins_24h"] == 1
    assert result["failed_logins_7d"][-1]["count"] == 1
