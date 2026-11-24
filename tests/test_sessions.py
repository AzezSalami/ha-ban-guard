"""Active sessions: listing, live removal, and disconnecting."""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import MagicMock

import aiohttp
import pytest
from pytest_homeassistant_custom_component.typing import (
    ClientSessionGenerator,
    WebSocketGenerator,
)

from custom_components.ban_guard.const import ACT_BLOCKED
from custom_components.ban_guard.manager import BanGuardError, BanGuardManager
from homeassistant.core import HomeAssistant

IP = "198.51.100.9"


async def _open_session(client: Any, token: str, ip: str = IP) -> Any:
    ws = await client.ws_connect(
        "/api/websocket", headers={"X-Forwarded-For": ip, "User-Agent": "TestBrowser/1.0"}
    )
    assert (await ws.receive_json())["type"] == "auth_required"
    await ws.send_json({"type": "auth", "access_token": token})
    assert (await ws.receive_json())["type"] == "auth_ok"
    return ws


async def _call(ws: Any, **data: Any) -> dict[str, Any]:
    await ws.send_json_auto_id(data)
    while True:
        msg = await ws.receive_json()
        if msg["type"] == "result":
            return msg  # type: ignore[no-any-return]


async def _wait_until(predicate: Any, timeout: float = 5) -> None:
    async with asyncio.timeout(timeout):
        while not predicate():
            await asyncio.sleep(0.01)


async def test_list_and_disconnect_end_to_end(
    hass: HomeAssistant,
    manager: BanGuardManager,
    hass_client_no_auth: ClientSessionGenerator,
    hass_ws_client: WebSocketGenerator,
    hass_access_token: str,
    hass_admin_user: Any,
) -> None:
    client = await hass_client_no_auth()
    phone = await _open_session(client, hass_access_token)
    admin = await hass_ws_client(hass)  # the admin's own panel connection

    msg = await _call(admin, type="ban_guard/sessions")
    assert msg["result"]["available"] is True
    sessions = msg["result"]["sessions"]
    remote = next(s for s in sessions if s["ip"] == IP)
    own = next(s for s in sessions if s["current"])
    assert remote["user"] == hass_admin_user.name
    assert remote["client_id"]
    assert remote["user_agent"] == "TestBrowser/1.0"
    assert remote["current"] is False
    assert remote["protected"] is False
    assert own["ip"] == "127.0.0.1"
    assert own["protected"] is True  # loopback
    assert manager.status()["open_sessions"] == len(sessions)

    # You cannot disconnect the session you are using.
    msg = await _call(admin, type="ban_guard/disconnect", session_id=own["id"])
    assert msg["error"]["code"] == "session_current"

    msg = await _call(admin, type="ban_guard/disconnect", session_id=remote["id"])
    assert msg["success"]
    closed = await phone.receive(timeout=5)
    assert closed.type in (
        aiohttp.WSMsgType.CLOSE,
        aiohttp.WSMsgType.CLOSED,
        aiohttp.WSMsgType.ERROR,
    )
    entry = manager.activity.entries(types={ACT_BLOCKED})[0]
    assert (entry.ip, entry.detail) == (IP, "session_disconnected")
    assert entry.user == hass_admin_user.name

    msg = await _call(admin, type="ban_guard/disconnect", session_id=remote["id"])
    assert msg["error"]["code"] == "session_not_found"


async def test_session_removed_when_client_leaves(
    hass: HomeAssistant,
    manager: BanGuardManager,
    hass_client_no_auth: ClientSessionGenerator,
    hass_access_token: str,
) -> None:
    client = await hass_client_no_auth()
    ws = await _open_session(client, hass_access_token)
    await _wait_until(lambda: any(str(s.addr) == IP for s in manager._sessions.values()))
    await ws.close()
    await _wait_until(lambda: not any(str(s.addr) == IP for s in manager._sessions.values()))


async def test_sessions_view_prunes_and_sorts(
    hass: HomeAssistant, manager: BanGuardManager
) -> None:
    def fake(ip: str, closing: bool = False) -> MagicMock:
        request = MagicMock(remote=ip, headers={"User-Agent": "x"})
        request.transport.is_closing.return_value = closing
        request.task = None
        manager.hook_session_opened(request, {"user": "Alex"})
        return request

    first = fake("198.51.100.1")
    second = fake("198.51.100.2")
    rows = manager.sessions_view()
    assert [r["ip"] for r in rows] == ["198.51.100.2", "198.51.100.1"]
    assert rows[0]["user"] == "Alex"
    second.transport.is_closing.return_value = True
    assert [r["ip"] for r in manager.sessions_view()] == ["198.51.100.1"]
    # A transport that errors counts as gone.
    first.transport.is_closing.side_effect = RuntimeError
    assert manager.sessions_view() == []
    # No info dict and no task attribute: still tracked.
    request = MagicMock(
        spec=["remote", "transport", "headers"], remote="198.51.100.3", headers=None
    )
    request.transport.is_closing.return_value = False
    manager.hook_session_opened(request)
    assert manager.sessions_view()[0]["user"] is None
    with pytest.raises(BanGuardError):
        await manager.async_disconnect("nope", user=None)
