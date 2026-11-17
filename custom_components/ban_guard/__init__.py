"""Ban Guard: manage IP bans, allowlist and failed-login protection."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN
from .manager import BanGuardManager
from .panel import async_register_panel, async_unregister_panel
from .services import async_register_services
from .websocket import async_register_websocket

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.SENSOR]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

type BanGuardConfigEntry = ConfigEntry[BanGuardManager]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register services and websocket commands once."""
    async_register_services(hass)
    async_register_websocket(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: BanGuardConfigEntry) -> bool:
    """Set up Ban Guard from a config entry."""
    manager = BanGuardManager(hass, entry)
    await manager.async_setup()
    entry.runtime_data = manager
    await async_register_panel(hass)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _async_update_listener(hass: HomeAssistant, entry: BanGuardConfigEntry) -> None:
    """Reload on options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: BanGuardConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        await entry.runtime_data.async_unload()
        async_unregister_panel(hass)
    return unloaded


async def async_remove_entry(hass: HomeAssistant, entry: BanGuardConfigEntry) -> None:
    """Remove stored data when the integration is deleted.

    Bans already mirrored to ip_bans.yaml stay there so HA keeps enforcing them.
    """
    from homeassistant.helpers.storage import Store  # noqa: PLC0415

    from .const import (  # noqa: PLC0415
        STORAGE_KEY_ACTIVITY,
        STORAGE_KEY_DATA,
        STORAGE_KEY_SECRET,
        STORAGE_VERSION,
    )

    for key in (STORAGE_KEY_DATA, STORAGE_KEY_ACTIVITY, STORAGE_KEY_SECRET):
        await Store[dict[str, object]](hass, STORAGE_VERSION, key).async_remove()
