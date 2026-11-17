"""Ban Guard sensors."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import ACT_BAN, ACT_FAILED_LOGIN
from .entity import BanGuardEntity

if TYPE_CHECKING:
    from . import BanGuardConfigEntry

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BanGuardConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up sensors."""
    manager = entry.runtime_data
    async_add_entities(
        [
            ActiveBansSensor(manager, "active_bans"),
            CountSensor(manager, "bans_24h", ACT_BAN),
            CountSensor(manager, "failed_logins_24h", ACT_FAILED_LOGIN),
            LastBannedSensor(manager, "last_banned_ip"),
        ]
    )


class ActiveBansSensor(BanGuardEntity, SensorEntity):
    """Number of active bans."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "bans"

    @property
    def native_value(self) -> int:
        """Active bans."""
        return len(self.manager.active_bans())

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Break down by kind."""
        bans = self.manager.active_bans()
        return {
            "permanent": sum(1 for b in bans if b.permanent),
            "temporary": sum(1 for b in bans if not b.permanent),
            "networks": sum(1 for b in bans if not b.single),
        }


class CountSensor(BanGuardEntity, SensorEntity):
    """Activity count over the last 24 hours."""

    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, manager: Any, key: str, activity_type: str) -> None:
        """Init."""
        super().__init__(manager, key)
        self._type = activity_type
        self._attr_native_unit_of_measurement = "bans" if activity_type == ACT_BAN else "attempts"

    @property
    def native_value(self) -> int:
        """Count."""
        since = dt_util.utcnow() - timedelta(days=1)
        return self.manager.activity.count_since(self._type, since)


class LastBannedSensor(BanGuardEntity, SensorEntity):
    """The most recently banned address."""

    @property
    def native_value(self) -> str | None:
        """IP or network."""
        return self.manager.last_ban["ip"] if self.manager.last_ban else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Ban details."""
        if not self.manager.last_ban:
            return {}
        return {k: v for k, v in self.manager.last_ban.items() if k != "ip"}
