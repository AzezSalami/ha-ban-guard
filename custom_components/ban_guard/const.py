"""Constants for Ban Guard."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "ban_guard"
NAME: Final = "Ban Guard"

EVENT_BAN_GUARD: Final = "ban_guard_event"
SIGNAL_UPDATE: Final = "ban_guard_update"
SIGNAL_ACTIVITY: Final = "ban_guard_activity"

STORAGE_VERSION: Final = 1
STORAGE_KEY_DATA: Final = f"{DOMAIN}.data"
STORAGE_KEY_ACTIVITY: Final = f"{DOMAIN}.activity"
STORAGE_KEY_SECRET: Final = f"{DOMAIN}.secret"

PANEL_URL_PATH: Final = "ban-guard"
PANEL_COMPONENT: Final = "ban-guard-panel"
PANEL_STATIC_URL: Final = "/ban_guard_static"
PANEL_FILENAME: Final = "ban-guard-panel.js"
PANEL_ICON: Final = "mdi:shield-lock"

# Ban sources
SOURCE_MANUAL: Final = "manual"
SOURCE_AUTOMATIC: Final = "automatic"
SOURCE_IMPORTED: Final = "imported"
SOURCE_SERVICE: Final = "service"
SOURCE_HOME_ASSISTANT: Final = "home_assistant"
SOURCES: Final = (
    SOURCE_MANUAL,
    SOURCE_AUTOMATIC,
    SOURCE_IMPORTED,
    SOURCE_SERVICE,
    SOURCE_HOME_ASSISTANT,
)

# Activity types
ACT_FAILED_LOGIN: Final = "failed_login"
ACT_LOGIN: Final = "login"
ACT_ALLOWLISTED_FAILURE: Final = "allowlisted_failure"
ACT_BAN: Final = "ban"
ACT_UNBAN: Final = "unban"
ACT_EXPIRED: Final = "expired"
ACT_BLOCKED: Final = "blocked"
ACT_ALLOW: Final = "allow"
ACT_DISALLOW: Final = "disallow"
ACT_REFUSED: Final = "refused"

# Event types (data["type"] of ban_guard_event)
EVT_BAN: Final = "ban"
EVT_UNBAN: Final = "unban"
EVT_REPEATED_FAILURES: Final = "repeated_failures"
EVT_ALLOWLISTED_FAILURE: Final = "allowlisted_failure"

# Option keys
CONF_PROTECTION_ENABLED: Final = "protection_enabled"
CONF_THRESHOLD: Final = "threshold"
CONF_WINDOW_MINUTES: Final = "window_minutes"
CONF_ESCALATION: Final = "escalation"
CONF_NETWORK_OVERRIDES: Final = "network_overrides"
CONF_ATTACK_THRESHOLD: Final = "attack_threshold"
CONF_ATTACK_WINDOW_MINUTES: Final = "attack_window_minutes"
CONF_NOTIFY_PERSISTENT: Final = "notify_persistent"
CONF_NOTIFY_ALLOWLISTED: Final = "notify_allowlisted_failures"
CONF_REPEATED_FAILURES: Final = "repeated_failures_threshold"
CONF_LOG_RETENTION_DAYS: Final = "log_retention_days"
CONF_LOG_MAX_ENTRIES: Final = "log_max_entries"
CONF_LOG_BLOCKED: Final = "log_blocked_requests"
CONF_LOG_LOGINS: Final = "log_successful_logins"
CONF_ALLOWLIST_REFRESH_MINUTES: Final = "allowlist_refresh_minutes"
CONF_GEOIP_ENABLED: Final = "geoip_enabled"
CONF_GEOIP_EDITION: Final = "geoip_edition"
CONF_GEOIP_MAX_MB: Final = "geoip_max_mb"
CONF_COUNTRY_ALLOW: Final = "country_allow"
CONF_COUNTRY_DENY: Final = "country_deny"
CONF_RDNS_ENABLED: Final = "rdns_enabled"
CONF_DOH_ENABLED: Final = "doh_enabled"
CONF_DOH_URL: Final = "doh_url"
CONF_NPM_ENABLED: Final = "npm_enabled"
CONF_NPM_URL: Final = "npm_url"
CONF_NPM_USERNAME: Final = "npm_username"
CONF_NPM_PASSWORD: Final = "npm_password"  # noqa: S105 - option key, not a secret
CONF_NPM_SECRET: Final = "npm_secret"  # noqa: S105 - encrypted blob key
CONF_NPM_ACCESS_LIST_ID: Final = "npm_access_list_id"
CONF_NPM_VERIFY_SSL: Final = "npm_verify_ssl"

GEOIP_EDITION_COUNTRY: Final = "country"
GEOIP_EDITION_CITY: Final = "city"

DEFAULT_OPTIONS: Final[dict[str, object]] = {
    CONF_PROTECTION_ENABLED: True,
    CONF_THRESHOLD: 5,
    CONF_WINDOW_MINUTES: 15,
    CONF_ESCALATION: "1h, 24h, permanent",
    CONF_NETWORK_OVERRIDES: "",
    CONF_ATTACK_THRESHOLD: 20,
    CONF_ATTACK_WINDOW_MINUTES: 10,
    CONF_NOTIFY_PERSISTENT: True,
    CONF_NOTIFY_ALLOWLISTED: True,
    CONF_REPEATED_FAILURES: 3,
    CONF_LOG_RETENTION_DAYS: 30,
    CONF_LOG_MAX_ENTRIES: 5000,
    CONF_LOG_BLOCKED: True,
    CONF_LOG_LOGINS: True,
    CONF_ALLOWLIST_REFRESH_MINUTES: 30,
    CONF_GEOIP_ENABLED: False,
    CONF_GEOIP_EDITION: GEOIP_EDITION_COUNTRY,
    CONF_GEOIP_MAX_MB: 200,
    CONF_COUNTRY_ALLOW: "",
    CONF_COUNTRY_DENY: "",
    CONF_RDNS_ENABLED: False,
    CONF_DOH_ENABLED: False,
    CONF_DOH_URL: "https://cloudflare-dns.com/dns-query",
    CONF_NPM_ENABLED: False,
    CONF_NPM_URL: "",
    CONF_NPM_USERNAME: "",
    CONF_NPM_ACCESS_LIST_ID: 0,
    CONF_NPM_VERIFY_SSL: True,
}

# Hard limits
MAX_REASON_LENGTH: Final = 200
MAX_USER_AGENT_LENGTH: Final = 256
MAX_PATH_LENGTH: Final = 256
MAX_IMPORT_ITEMS: Final = 10000
BLOCKED_LOG_INTERVAL_SECONDS: Final = 60

# Home Assistant OS / Supervised internal Docker network.
SUPERVISOR_NETWORK: Final = "172.30.32.0/23"

# Issue ids
ISSUE_HOOK_INCOMPATIBLE: Final = "hook_incompatible"
ISSUE_BANS_DISABLED: Final = "ip_ban_disabled"
ISSUE_HOOK_ERROR: Final = "hook_runtime_error"
ISSUE_GEOIP_FAILED: Final = "geoip_failed"
ISSUE_NPM_FAILED: Final = "npm_failed"

GEOIP_URL_TEMPLATE: Final = "https://download.db-ip.com/free/dbip-{edition}-lite-{month}.mmdb.gz"
GEOIP_DIRNAME: Final = "ban_guard"
