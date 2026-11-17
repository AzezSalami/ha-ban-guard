"""Read and write Home Assistant's ip_bans.yaml (blocking: run in executor)."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import datetime
import logging
import os
from typing import Any

from homeassistant.exceptions import HomeAssistantError
from homeassistant.util import dt as dt_util
from homeassistant.util.file import write_utf8_file_atomic
from homeassistant.util.yaml import dump, load_yaml

from .iputil import InvalidTargetError, parse_address

_LOGGER = logging.getLogger(__name__)


def _load_raw(path: str) -> dict[str, Any]:
    if not os.path.isfile(path):
        return {}
    try:
        data = load_yaml(path)
    except HomeAssistantError as err:
        _LOGGER.error("Unable to read %s: %s", path, err)
        raise
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise HomeAssistantError(f"{path} does not contain a mapping")
    return {str(k): v for k, v in data.items()}


def read_bans(path: str, attr_banned_at: str = "banned_at") -> dict[str, datetime]:
    """Return {ip: banned_at} for every valid entry in the file."""
    result: dict[str, datetime] = {}
    for key, info in _load_raw(path).items():
        try:
            addr = parse_address(key)
        except InvalidTargetError:
            _LOGGER.warning("Ignoring invalid entry %r in %s", key, path)
            continue
        banned_at: datetime | None = None
        if isinstance(info, Mapping) and info.get(attr_banned_at):
            value = info[attr_banned_at]
            banned_at = value if isinstance(value, datetime) else dt_util.parse_datetime(str(value))
        if banned_at is None:
            banned_at = dt_util.utcnow()
        elif banned_at.tzinfo is None:
            banned_at = banned_at.replace(tzinfo=dt_util.UTC)
        result[str(addr)] = banned_at
    return result


def update_bans(
    path: str,
    add: Mapping[str, datetime],
    remove: Iterable[str],
    attr_banned_at: str = "banned_at",
) -> None:
    """Apply additions and removals atomically, preserving unrelated entries."""
    raw = _load_raw(path)
    removals = set(remove)
    normalized: dict[str, Any] = {}
    for key, info in raw.items():
        try:
            canonical = str(parse_address(key))
        except InvalidTargetError:
            normalized[key] = info  # keep what we do not understand
            continue
        if canonical in removals:
            continue
        normalized[canonical] = info
    for ip, banned_at in add.items():
        normalized[ip] = {attr_banned_at: banned_at.isoformat()}
    content = dump(normalized) if normalized else ""
    write_utf8_file_atomic(path, content, private=True)
