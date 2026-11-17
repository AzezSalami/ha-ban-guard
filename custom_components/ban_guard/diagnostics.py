"""Diagnostics with every IP address redacted."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING, Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from .const import CONF_DOH_URL, CONF_NPM_SECRET, CONF_NPM_URL, CONF_NPM_USERNAME

if TYPE_CHECKING:
    from . import BanGuardConfigEntry

TO_REDACT = {
    CONF_NPM_SECRET,
    CONF_NPM_URL,
    CONF_NPM_USERNAME,
    CONF_DOH_URL,
    "created_by",
    "user",
    "user_agent",
    "path",
    "comment",
    "detail",
    "reason",
    "network_overrides",
}
# Keys whose values are IP addresses, networks or hostnames.
IP_KEYS = {"ip", "value", "resolved"}


def _token(value: str) -> str:
    """Stable, non-reversible token so entries can still be correlated."""
    return f"<ip:{hashlib.sha256(value.encode()).hexdigest()[:8]}>"


def redact_ips(data: Any) -> Any:
    """Replace values of IP_KEYS with tokens, recursively."""
    if isinstance(data, dict):
        result: dict[str, Any] = {}
        for key, value in data.items():
            if key in IP_KEYS and isinstance(value, str):
                result[key] = _token(value)
            elif key in IP_KEYS and isinstance(value, list):
                result[key] = [_token(str(v)) for v in value]
            else:
                result[key] = redact_ips(value)
        return result
    if isinstance(data, list):
        return [redact_ips(v) for v in data]
    return data


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: BanGuardConfigEntry
) -> dict[str, Any]:
    """Return diagnostics."""
    manager = entry.runtime_data
    data = {
        "options": dict(entry.options),
        "status": manager.status(),
        "counts": {
            "bans": len(manager.bans),
            "active_bans": len(manager.active_bans()),
            "allowlist": len(manager.allow),
            "activity_entries": len(manager.activity),
            "offenses": len(manager.offenses),
        },
        "bans": [b.as_dict() for b in manager.bans.values()],
        "last_ban": manager.last_ban,
        "allowlist": [a.as_dict() for a in manager.allow.values()],
        "recent_activity": [e.as_dict() for e in manager.activity.entries(limit=50)],
    }
    return redact_ips(async_redact_data(data, TO_REDACT))  # type: ignore[no-any-return]
