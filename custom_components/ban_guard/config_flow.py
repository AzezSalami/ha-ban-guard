"""Config and options flow for Ban Guard."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_ALLOWLIST_REFRESH_MINUTES,
    CONF_ATTACK_THRESHOLD,
    CONF_ATTACK_WINDOW_MINUTES,
    CONF_COUNTRY_ALLOW,
    CONF_COUNTRY_DENY,
    CONF_DOH_ENABLED,
    CONF_DOH_URL,
    CONF_ESCALATION,
    CONF_GEOIP_EDITION,
    CONF_GEOIP_ENABLED,
    CONF_GEOIP_MAX_MB,
    CONF_LOG_BLOCKED,
    CONF_LOG_MAX_ENTRIES,
    CONF_LOG_RETENTION_DAYS,
    CONF_NETWORK_OVERRIDES,
    CONF_NOTIFY_ALLOWLISTED,
    CONF_NOTIFY_PERSISTENT,
    CONF_NPM_ACCESS_LIST_ID,
    CONF_NPM_ENABLED,
    CONF_NPM_PASSWORD,
    CONF_NPM_SECRET,
    CONF_NPM_URL,
    CONF_NPM_USERNAME,
    CONF_NPM_VERIFY_SSL,
    CONF_PROTECTION_ENABLED,
    CONF_RDNS_ENABLED,
    CONF_REPEATED_FAILURES,
    CONF_THRESHOLD,
    CONF_WINDOW_MINUTES,
    DOMAIN,
    GEOIP_EDITION_CITY,
    GEOIP_EDITION_COUNTRY,
    NAME,
)
from .npm import NPMClient, NPMError, async_detect_addon
from .secret import SecretBox
from .settings import SettingsError, country_rules, merged, protection_settings


def _number(minimum: int, maximum: int, unit: str | None = None) -> selector.NumberSelector:
    config = selector.NumberSelectorConfig(
        min=minimum, max=maximum, step=1, mode=selector.NumberSelectorMode.BOX
    )
    if unit is not None:
        config["unit_of_measurement"] = unit
    return selector.NumberSelector(config)


_TEXT = selector.TextSelector()
_MULTILINE = selector.TextSelector(selector.TextSelectorConfig(multiline=True))
_URL = selector.TextSelector(selector.TextSelectorConfig(type=selector.TextSelectorType.URL))
_PASSWORD = selector.TextSelector(
    selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
)
_BOOL = selector.BooleanSelector()


class BanGuardConfigFlow(ConfigFlow, domain=DOMAIN):
    """Initial setup: one confirmation step."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Confirm setup."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        if user_input is not None:
            return self.async_create_entry(
                title=NAME,
                data={},
                options={CONF_PROTECTION_ENABLED: user_input[CONF_PROTECTION_ENABLED]},
            )
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_PROTECTION_ENABLED, default=True): _BOOL}),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> BanGuardOptionsFlow:
        """Options flow."""
        return BanGuardOptionsFlow()


class BanGuardOptionsFlow(OptionsFlow):
    """Every setting, grouped into steps reachable from a menu."""

    def __init__(self) -> None:
        """Init."""
        self._npm_pending: dict[str, Any] = {}
        self._npm_lists: list[dict[str, Any]] = []

    @property
    def _opts(self) -> dict[str, Any]:
        return merged(self.config_entry.options)

    def _save(self, update: dict[str, Any]) -> ConfigFlowResult:
        options = dict(self.config_entry.options)
        options.update(update)
        return self.async_create_entry(data=options)

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Menu."""
        return self.async_show_menu(
            step_id="init",
            menu_options=[
                "protection",
                "notifications",
                "logging",
                "enrichment",
                "countries",
                "npm",
            ],
        )

    async def async_step_protection(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Failed-login protection."""
        errors: dict[str, str] = {}
        opts = self._opts
        if user_input is not None:
            user_input = _ints(
                user_input,
                CONF_THRESHOLD,
                CONF_WINDOW_MINUTES,
                CONF_ATTACK_THRESHOLD,
                CONF_ATTACK_WINDOW_MINUTES,
                CONF_REPEATED_FAILURES,
            )
            user_input.setdefault(CONF_NETWORK_OVERRIDES, "")
            try:
                protection_settings({**opts, **user_input})
            except SettingsError as err:
                errors["base"] = err.key
            else:
                return self._save(user_input)
        schema = vol.Schema(
            {
                vol.Required(CONF_PROTECTION_ENABLED, default=opts[CONF_PROTECTION_ENABLED]): _BOOL,
                vol.Required(CONF_THRESHOLD, default=opts[CONF_THRESHOLD]): _number(1, 1000),
                vol.Required(CONF_WINDOW_MINUTES, default=opts[CONF_WINDOW_MINUTES]): _number(
                    1, 10080, "min"
                ),
                vol.Required(CONF_ESCALATION, default=opts[CONF_ESCALATION]): _TEXT,
                vol.Optional(
                    CONF_NETWORK_OVERRIDES,
                    description={"suggested_value": opts[CONF_NETWORK_OVERRIDES]},
                ): _MULTILINE,
                vol.Required(CONF_REPEATED_FAILURES, default=opts[CONF_REPEATED_FAILURES]): _number(
                    0, 1000
                ),
                vol.Required(CONF_ATTACK_THRESHOLD, default=opts[CONF_ATTACK_THRESHOLD]): _number(
                    1, 100000
                ),
                vol.Required(
                    CONF_ATTACK_WINDOW_MINUTES, default=opts[CONF_ATTACK_WINDOW_MINUTES]
                ): _number(1, 1440, "min"),
            }
        )
        return self.async_show_form(step_id="protection", data_schema=schema, errors=errors)

    async def async_step_notifications(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Notifications."""
        if user_input is not None:
            return self._save(user_input)
        opts = self._opts
        schema = vol.Schema(
            {
                vol.Required(CONF_NOTIFY_PERSISTENT, default=opts[CONF_NOTIFY_PERSISTENT]): _BOOL,
                vol.Required(CONF_NOTIFY_ALLOWLISTED, default=opts[CONF_NOTIFY_ALLOWLISTED]): _BOOL,
            }
        )
        return self.async_show_form(step_id="notifications", data_schema=schema)

    async def async_step_logging(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Activity log and allowlist refresh."""
        if user_input is not None:
            return self._save(
                _ints(
                    user_input,
                    CONF_LOG_RETENTION_DAYS,
                    CONF_LOG_MAX_ENTRIES,
                    CONF_ALLOWLIST_REFRESH_MINUTES,
                )
            )
        opts = self._opts
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_LOG_RETENTION_DAYS, default=opts[CONF_LOG_RETENTION_DAYS]
                ): _number(1, 365, "d"),
                vol.Required(CONF_LOG_MAX_ENTRIES, default=opts[CONF_LOG_MAX_ENTRIES]): _number(
                    100, 100000
                ),
                vol.Required(CONF_LOG_BLOCKED, default=opts[CONF_LOG_BLOCKED]): _BOOL,
                vol.Required(
                    CONF_ALLOWLIST_REFRESH_MINUTES, default=opts[CONF_ALLOWLIST_REFRESH_MINUTES]
                ): _number(1, 1440, "min"),
            }
        )
        return self.async_show_form(step_id="logging", data_schema=schema)

    async def async_step_enrichment(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """GeoIP, reverse DNS and DNS-over-HTTPS. Each sends data; the form says what."""
        errors: dict[str, str] = {}
        if user_input is not None:
            user_input = _ints(user_input, CONF_GEOIP_MAX_MB)
            if user_input.get(CONF_DOH_ENABLED) and not str(
                user_input.get(CONF_DOH_URL, "")
            ).startswith("https://"):
                errors[CONF_DOH_URL] = "invalid_doh_url"
            else:
                return self._save(user_input)
        opts = self._opts
        schema = vol.Schema(
            {
                vol.Required(CONF_GEOIP_ENABLED, default=opts[CONF_GEOIP_ENABLED]): _BOOL,
                vol.Required(CONF_GEOIP_EDITION, default=opts[CONF_GEOIP_EDITION]): (
                    selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[GEOIP_EDITION_COUNTRY, GEOIP_EDITION_CITY],
                            translation_key="geoip_edition",
                        )
                    )
                ),
                vol.Required(CONF_GEOIP_MAX_MB, default=opts[CONF_GEOIP_MAX_MB]): _number(
                    10, 1024, "MB"
                ),
                vol.Required(CONF_RDNS_ENABLED, default=opts[CONF_RDNS_ENABLED]): _BOOL,
                vol.Required(CONF_DOH_ENABLED, default=opts[CONF_DOH_ENABLED]): _BOOL,
                vol.Required(CONF_DOH_URL, default=opts[CONF_DOH_URL]): _URL,
            }
        )
        return self.async_show_form(step_id="enrichment", data_schema=schema, errors=errors)

    async def async_step_countries(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Country allow/deny rules (need GeoIP)."""
        errors: dict[str, str] = {}
        opts = self._opts
        if user_input is not None:
            user_input.setdefault(CONF_COUNTRY_ALLOW, "")
            user_input.setdefault(CONF_COUNTRY_DENY, "")
            try:
                allow, deny = country_rules(user_input)
            except SettingsError as err:
                errors["base"] = err.key
            else:
                if (allow or deny) and not opts[CONF_GEOIP_ENABLED]:
                    errors["base"] = "geoip_required"
                else:
                    return self._save(
                        {
                            CONF_COUNTRY_ALLOW: ", ".join(sorted(allow)),
                            CONF_COUNTRY_DENY: ", ".join(sorted(deny)),
                        }
                    )
        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_COUNTRY_ALLOW, description={"suggested_value": opts[CONF_COUNTRY_ALLOW]}
                ): _TEXT,
                vol.Optional(
                    CONF_COUNTRY_DENY, description={"suggested_value": opts[CONF_COUNTRY_DENY]}
                ): _TEXT,
            }
        )
        return self.async_show_form(step_id="countries", data_schema=schema, errors=errors)

    async def async_step_npm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Nginx Proxy Manager connection."""
        errors: dict[str, str] = {}
        opts = self._opts
        if user_input is not None:
            if not user_input[CONF_NPM_ENABLED]:
                return self._save({CONF_NPM_ENABLED: False})
            password = user_input.get(CONF_NPM_PASSWORD) or ""
            box = SecretBox(self.hass)
            if not password and opts.get(CONF_NPM_SECRET):
                password = await box.async_decrypt(str(opts[CONF_NPM_SECRET])) or ""
            client = NPMClient(
                self.hass,
                user_input[CONF_NPM_URL],
                user_input[CONF_NPM_USERNAME],
                password,
                user_input[CONF_NPM_VERIFY_SSL],
            )
            try:
                self._npm_lists = await client.async_access_lists()
            except NPMError as err:
                errors["base"] = err.key
            else:
                if not self._npm_lists:
                    errors["base"] = "no_access_lists"
                else:
                    self._npm_pending = {
                        CONF_NPM_ENABLED: True,
                        CONF_NPM_URL: user_input[CONF_NPM_URL],
                        CONF_NPM_USERNAME: user_input[CONF_NPM_USERNAME],
                        CONF_NPM_VERIFY_SSL: user_input[CONF_NPM_VERIFY_SSL],
                        CONF_NPM_SECRET: await box.async_encrypt(password),
                    }
                    return await self.async_step_npm_list()
        addon = await async_detect_addon(self.hass)
        default_url = opts[CONF_NPM_URL] or (addon["suggested_url"] if addon else "")
        schema = vol.Schema(
            {
                vol.Required(CONF_NPM_ENABLED, default=opts[CONF_NPM_ENABLED]): _BOOL,
                vol.Required(CONF_NPM_URL, default=default_url): _URL,
                vol.Required(CONF_NPM_USERNAME, default=opts[CONF_NPM_USERNAME]): _TEXT,
                vol.Optional(CONF_NPM_PASSWORD): _PASSWORD,
                vol.Required(CONF_NPM_VERIFY_SSL, default=opts[CONF_NPM_VERIFY_SSL]): _BOOL,
            }
        )
        return self.async_show_form(
            step_id="npm",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "addon": addon["name"] if addon else "-",
            },
        )

    async def async_step_npm_list(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Pick the access list Ban Guard owns."""
        if user_input is not None:
            return self._save(
                {
                    **self._npm_pending,
                    CONF_NPM_ACCESS_LIST_ID: int(user_input[CONF_NPM_ACCESS_LIST_ID]),
                }
            )
        options = [
            selector.SelectOptionDict(
                value=str(item["id"]), label=f"{item['name']} (#{item['id']})"
            )
            for item in self._npm_lists
        ]
        schema = vol.Schema(
            {
                vol.Required(CONF_NPM_ACCESS_LIST_ID): selector.SelectSelector(
                    selector.SelectSelectorConfig(options=options)
                )
            }
        )
        return self.async_show_form(step_id="npm_list", data_schema=schema)


def _ints(data: dict[str, Any], *keys: str) -> dict[str, Any]:
    """Number selectors return floats; store ints."""
    result = dict(data)
    for key in keys:
        if key in result and result[key] is not None:
            result[key] = int(result[key])
    return result
