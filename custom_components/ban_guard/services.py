"""Ban Guard services (admin only)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import voluptuous as vol

from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
    callback,
)
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.http import current_request
from homeassistant.helpers.service import async_register_admin_service

from .const import DOMAIN, SOURCE_SERVICE
from .iputil import IPAddress, normalize_address
from .settings import SettingsError, parse_duration

if TYPE_CHECKING:
    from .manager import BanGuardManager

ATTR_IP = "ip"
ATTR_REASON = "reason"
ATTR_DURATION = "duration"
ATTR_VALUE = "value"
ATTR_COMMENT = "comment"
ATTR_DATA = "data"
ATTR_DRY_RUN = "dry_run"
ATTR_INCLUDE_SETTINGS = "include_settings"

SCHEMA_BAN = vol.Schema(
    {
        vol.Required(ATTR_IP): cv.string,
        vol.Optional(ATTR_REASON, default=""): cv.string,
        vol.Optional(ATTR_DURATION, default="permanent"): cv.string,
    }
)
SCHEMA_UNBAN = vol.Schema({vol.Required(ATTR_IP): vol.All(cv.ensure_list, [cv.string])})
SCHEMA_ALLOW = vol.Schema(
    {
        vol.Required(ATTR_VALUE): cv.string,
        vol.Optional(ATTR_COMMENT, default=""): cv.string,
    }
)
SCHEMA_DISALLOW = vol.Schema({vol.Required(ATTR_VALUE): cv.string})
SCHEMA_EMPTY = vol.Schema({})
SCHEMA_IMPORT = vol.Schema(
    {
        vol.Required(ATTR_DATA): dict,
        vol.Optional(ATTR_DRY_RUN, default=True): cv.boolean,
        vol.Optional(ATTR_INCLUDE_SETTINGS, default=False): cv.boolean,
    }
)


def get_manager(hass: HomeAssistant) -> BanGuardManager:
    """Return the loaded manager or raise."""
    for entry in hass.config_entries.async_loaded_entries(DOMAIN):
        return entry.runtime_data  # type: ignore[no-any-return]
    raise ServiceValidationError(translation_domain=DOMAIN, translation_key="not_loaded")


def requester_ip() -> IPAddress | None:
    """IP of the HTTP/websocket client making the current call, if any."""
    import ipaddress  # noqa: PLC0415

    request = current_request.get()
    if request is None or not request.remote:
        return None
    try:
        return normalize_address(ipaddress.ip_address(request.remote))
    except ValueError:
        return None


@callback
def async_register_services(hass: HomeAssistant) -> None:
    """Register services."""

    async def ban(call: ServiceCall) -> None:
        manager = get_manager(hass)
        try:
            duration = parse_duration(call.data[ATTR_DURATION])
        except SettingsError as err:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="invalid_duration",
                translation_placeholders={"value": call.data[ATTR_DURATION]},
            ) from err
        await manager.async_ban(
            call.data[ATTR_IP],
            reason=call.data[ATTR_REASON],
            source=SOURCE_SERVICE,
            user=call.context.user_id,
            duration=duration,
            requester=requester_ip(),
        )

    async def unban(call: ServiceCall) -> None:
        await get_manager(hass).async_unban(call.data[ATTR_IP], user=call.context.user_id)

    async def allow(call: ServiceCall) -> None:
        await get_manager(hass).async_allow(
            call.data[ATTR_VALUE], comment=call.data[ATTR_COMMENT], user=call.context.user_id
        )

    async def disallow(call: ServiceCall) -> None:
        await get_manager(hass).async_disallow(call.data[ATTR_VALUE], user=call.context.user_id)

    async def purge_expired(call: ServiceCall) -> ServiceResponse:
        return {"lifted": await get_manager(hass).async_purge_expired()}

    async def import_(call: ServiceCall) -> ServiceResponse:
        manager = get_manager(hass)
        if call.data[ATTR_DRY_RUN]:
            preview = manager.validate_import(call.data[ATTR_DATA], requester_ip())
            return {"dry_run": True, "preview": preview}
        result = await manager.async_import(
            call.data[ATTR_DATA],
            user=call.context.user_id,
            requester=requester_ip(),
            include_settings=call.data[ATTR_INCLUDE_SETTINGS],
        )
        return {"dry_run": False, "preview": result}

    async def export(call: ServiceCall) -> ServiceResponse:
        data: dict[str, Any] = get_manager(hass).export_data()
        return data

    async_register_admin_service(hass, DOMAIN, "ban", ban, SCHEMA_BAN)
    async_register_admin_service(hass, DOMAIN, "unban", unban, SCHEMA_UNBAN)
    async_register_admin_service(hass, DOMAIN, "allow", allow, SCHEMA_ALLOW)
    async_register_admin_service(hass, DOMAIN, "disallow", disallow, SCHEMA_DISALLOW)
    async_register_admin_service(
        hass,
        DOMAIN,
        "purge_expired",
        purge_expired,
        SCHEMA_EMPTY,
        supports_response=SupportsResponse.OPTIONAL,
    )
    async_register_admin_service(
        hass,
        DOMAIN,
        "import",
        import_,
        SCHEMA_IMPORT,
        supports_response=SupportsResponse.OPTIONAL,
    )
    async_register_admin_service(
        hass,
        DOMAIN,
        "export",
        export,
        SCHEMA_EMPTY,
        supports_response=SupportsResponse.ONLY,
    )
