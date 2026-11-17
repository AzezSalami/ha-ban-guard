"""Ban Guard 'under attack' binary sensor."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval

from .entity import BanGuardEntity

if TYPE_CHECKING:
    from . import BanGuardConfigEntry

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BanGuardConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the binary sensor."""
    async_add_entities([UnderAttackSensor(entry.runtime_data, "under_attack")])


class UnderAttackSensor(BanGuardEntity, BinarySensorEntity):
    """On when failed logins exceed the configured rate."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    async def async_added_to_hass(self) -> None:
        """Also re-evaluate every minute so the sensor turns off on its own."""
        await super().async_added_to_hass()
        self.async_on_remove(
            async_track_time_interval(self.hass, self._async_tick, timedelta(minutes=1))
        )

    @callback
    def _async_tick(self, _now: datetime) -> None:
        self.async_write_ha_state()

    @property
    def is_on(self) -> bool:
        """Under attack."""
        return self.manager.is_under_attack()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Rate details."""
        settings = self.manager.protection
        return {
            "failures_in_window": self.manager.recent_failure_count(),
            "threshold": settings.attack_threshold,
            "window_minutes": int(settings.attack_window.total_seconds() // 60),
        }
