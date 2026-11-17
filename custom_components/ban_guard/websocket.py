"""Websocket API for the admin panel. Every command requires an admin user."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
import functools
from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.dispatcher import async_dispatcher_connect

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
    CONF_NPM_SECRET,
    SIGNAL_UPDATE,
    SOURCE_MANUAL,
)
from .manager import BanGuardError, BanGuardManager
from .models import Activity
from .npm import async_detect_addon
from .services import get_manager, requester_ip
from .settings import SettingsError, parse_duration

ACTIVITY_TYPES = [
    ACT_FAILED_LOGIN,
    ACT_ALLOWLISTED_FAILURE,
    ACT_BAN,
    ACT_UNBAN,
    ACT_EXPIRED,
    ACT_BLOCKED,
    ACT_ALLOW,
    ACT_DISALLOW,
    ACT_REFUSED,
]

type _Handler = Callable[
    [HomeAssistant, websocket_api.ActiveConnection, dict[str, Any], BanGuardManager],
    Awaitable[None],
]


def _with_manager(
    func: _Handler,
) -> Callable[[HomeAssistant, websocket_api.ActiveConnection, dict[str, Any]], Awaitable[None]]:
    """Resolve the manager and translate errors."""

    @functools.wraps(func)
    async def wrapper(
        hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
    ) -> None:
        try:
            manager = get_manager(hass)
        except ServiceValidationError:
            connection.send_error(msg["id"], "not_loaded", "Ban Guard is not loaded")
            return
        try:
            await func(hass, connection, msg, manager)
        except BanGuardError as err:
            connection.send_error(
                msg["id"],
                err.key,
                str(err),
                translation_key=err.key,
                translation_domain="ban_guard",
                translation_placeholders=err.placeholders or None,
            )

    return wrapper


@callback
def async_register_websocket(hass: HomeAssistant) -> None:
    """Register all commands."""
    for command in (
        ws_overview,
        ws_bans,
        ws_ban,
        ws_unban,
        ws_restore,
        ws_allowlist,
        ws_allow,
        ws_disallow,
        ws_activity,
        ws_subscribe_activity,
        ws_subscribe_updates,
        ws_history,
        ws_export,
        ws_import,
        ws_settings,
        ws_npm_sync,
    ):
        websocket_api.async_register_command(hass, command)


@websocket_api.websocket_command({vol.Required("type"): "ban_guard/overview"})
@websocket_api.require_admin
@websocket_api.async_response
@_with_manager
async def ws_overview(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
    manager: BanGuardManager,
) -> None:
    """Stats for the overview page."""
    stats = manager.activity.stats(manager.country_of)
    connection.send_result(
        msg["id"],
        {
            "active_bans": len(manager.active_bans()),
            "allowlist": len(manager.allow),
            "recent_failures": manager.recent_failure_count(),
            "last_ban": manager.last_ban,
            "status": manager.status(),
            **stats,
        },
    )


@websocket_api.websocket_command({vol.Required("type"): "ban_guard/bans"})
@websocket_api.require_admin
@websocket_api.async_response
@_with_manager
async def ws_bans(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
    manager: BanGuardManager,
) -> None:
    """List active bans."""
    connection.send_result(
        msg["id"], {"bans": [manager.ban_view(b) for b in manager.active_bans()]}
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): "ban_guard/ban",
        vol.Required("ip"): str,
        vol.Optional("reason", default=""): str,
        vol.Optional("duration", default="permanent"): str,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
@_with_manager
async def ws_ban(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
    manager: BanGuardManager,
) -> None:
    """Ban an address."""
    try:
        duration = parse_duration(msg["duration"])
    except SettingsError as err:
        raise BanGuardError("invalid_duration", value=msg["duration"]) from err
    ban = await manager.async_ban(
        msg["ip"],
        reason=msg["reason"],
        source=SOURCE_MANUAL,
        user=connection.user.id,
        duration=duration,
        requester=requester_ip(),
    )
    connection.send_result(msg["id"], {"ban": manager.ban_view(ban)})


@websocket_api.websocket_command(
    {vol.Required("type"): "ban_guard/unban", vol.Required("ips"): [str]}
)
@websocket_api.require_admin
@websocket_api.async_response
@_with_manager
async def ws_unban(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
    manager: BanGuardManager,
) -> None:
    """Unban; returns removed bans so the panel can offer undo."""
    removed = await manager.async_unban(msg["ips"], user=connection.user.id)
    connection.send_result(msg["id"], {"removed": [b.as_dict() for b in removed]})


@websocket_api.websocket_command(
    {vol.Required("type"): "ban_guard/restore", vol.Required("bans"): [dict]}
)
@websocket_api.require_admin
@websocket_api.async_response
@_with_manager
async def ws_restore(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
    manager: BanGuardManager,
) -> None:
    """Undo an unban."""
    for raw in msg["bans"]:
        try:
            from .models import Ban  # noqa: PLC0415

            ban = Ban.from_dict(raw)
        except (KeyError, ValueError, TypeError) as err:
            raise BanGuardError("invalid_ip", ip=str(raw.get("ip"))) from err
        manager._check_lockout(ban.network, requester_ip())  # noqa: SLF001
    await manager.async_restore(msg["bans"])
    connection.send_result(msg["id"])


@websocket_api.websocket_command({vol.Required("type"): "ban_guard/allowlist"})
@websocket_api.require_admin
@websocket_api.async_response
@_with_manager
async def ws_allowlist(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
    manager: BanGuardManager,
) -> None:
    """List the allowlist."""
    connection.send_result(msg["id"], {"allowlist": [a.as_dict() for a in manager.allow.values()]})


@websocket_api.websocket_command(
    {
        vol.Required("type"): "ban_guard/allow",
        vol.Required("value"): str,
        vol.Optional("comment", default=""): str,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
@_with_manager
async def ws_allow(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
    manager: BanGuardManager,
) -> None:
    """Add to the allowlist."""
    entry = await manager.async_allow(msg["value"], comment=msg["comment"], user=connection.user.id)
    connection.send_result(msg["id"], {"entry": entry.as_dict()})


@websocket_api.websocket_command(
    {vol.Required("type"): "ban_guard/disallow", vol.Required("value"): str}
)
@websocket_api.require_admin
@websocket_api.async_response
@_with_manager
async def ws_disallow(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
    manager: BanGuardManager,
) -> None:
    """Remove from the allowlist."""
    entry = await manager.async_disallow(msg["value"], user=connection.user.id)
    connection.send_result(msg["id"], {"entry": entry.as_dict()})


@websocket_api.websocket_command(
    {
        vol.Required("type"): "ban_guard/activity",
        vol.Optional("limit", default=200): vol.All(int, vol.Range(min=1, max=1000)),
        vol.Optional("before_id"): int,
        vol.Optional("ip"): str,
        vol.Optional("types"): [vol.In(ACTIVITY_TYPES)],
    }
)
@websocket_api.require_admin
@websocket_api.async_response
@_with_manager
async def ws_activity(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
    manager: BanGuardManager,
) -> None:
    """Page through the activity log."""
    types = set(msg["types"]) if msg.get("types") else None
    entries = manager.activity.entries(
        limit=msg["limit"], before_id=msg.get("before_id"), ip=msg.get("ip"), types=types
    )
    connection.send_result(msg["id"], {"entries": [_activity_view(manager, e) for e in entries]})


def _activity_view(manager: BanGuardManager, entry: Activity) -> dict[str, Any]:
    data = entry.as_dict()
    data["country"] = manager.country_of(entry.ip)
    return data


@websocket_api.websocket_command({vol.Required("type"): "ban_guard/subscribe_activity"})
@websocket_api.require_admin
@websocket_api.async_response
@_with_manager
async def ws_subscribe_activity(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
    manager: BanGuardManager,
) -> None:
    """Stream new activity entries."""

    @callback
    def forward(entry: Activity) -> None:
        connection.send_message(
            websocket_api.event_message(msg["id"], {"entry": _activity_view(manager, entry)})
        )

    connection.subscriptions[msg["id"]] = manager.subscribe_activity(forward)
    connection.send_result(msg["id"])


@websocket_api.websocket_command({vol.Required("type"): "ban_guard/subscribe_updates"})
@websocket_api.require_admin
@websocket_api.async_response
@_with_manager
async def ws_subscribe_updates(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
    manager: BanGuardManager,
) -> None:
    """Notify the panel whenever bans, allowlist or counters change."""

    @callback
    def forward() -> None:
        connection.send_message(websocket_api.event_message(msg["id"], {"changed": True}))

    connection.subscriptions[msg["id"]] = async_dispatcher_connect(hass, SIGNAL_UPDATE, forward)
    connection.send_result(msg["id"])


@websocket_api.websocket_command(
    {vol.Required("type"): "ban_guard/history", vol.Required("ip"): str}
)
@websocket_api.require_admin
@websocket_api.async_response
@_with_manager
async def ws_history(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
    manager: BanGuardManager,
) -> None:
    """Everything known about one IP."""
    connection.send_result(msg["id"], await manager.async_history(msg["ip"]))


@websocket_api.websocket_command({vol.Required("type"): "ban_guard/export"})
@websocket_api.require_admin
@websocket_api.async_response
@_with_manager
async def ws_export(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
    manager: BanGuardManager,
) -> None:
    """Return a JSON backup."""
    connection.send_result(msg["id"], manager.export_data())


@websocket_api.websocket_command(
    {
        vol.Required("type"): "ban_guard/import",
        vol.Required("data"): dict,
        vol.Optional("dry_run", default=True): bool,
        vol.Optional("include_settings", default=False): bool,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
@_with_manager
async def ws_import(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
    manager: BanGuardManager,
) -> None:
    """Preview (dry run) or apply a backup."""
    if msg["dry_run"]:
        preview = manager.validate_import(msg["data"], requester_ip())
    else:
        preview = await manager.async_import(
            msg["data"],
            user=connection.user.id,
            requester=requester_ip(),
            include_settings=msg["include_settings"],
        )
    connection.send_result(msg["id"], {"dry_run": msg["dry_run"], "preview": preview})


@websocket_api.websocket_command({vol.Required("type"): "ban_guard/settings"})
@websocket_api.require_admin
@websocket_api.async_response
@_with_manager
async def ws_settings(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
    manager: BanGuardManager,
) -> None:
    """Current settings (secrets removed) and feature status."""
    options = {k: v for k, v in manager.options.items() if k != CONF_NPM_SECRET}
    connection.send_result(
        msg["id"],
        {
            "entry_id": manager.entry.entry_id,
            "options": options,
            "status": manager.status(),
            "requester_ip": str(ip) if (ip := requester_ip()) else None,
            "npm_addon": await async_detect_addon(hass),
        },
    )


@websocket_api.websocket_command({vol.Required("type"): "ban_guard/npm_sync"})
@websocket_api.require_admin
@websocket_api.async_response
@_with_manager
async def ws_npm_sync(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
    manager: BanGuardManager,
) -> None:
    """Sync to Nginx Proxy Manager now."""
    await manager.async_npm_sync()
    connection.send_result(msg["id"], manager.npm_status)
