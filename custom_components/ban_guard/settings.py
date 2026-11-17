"""Parse and validate Ban Guard options."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import timedelta
import re
from typing import Any

from .const import (
    CONF_ATTACK_THRESHOLD,
    CONF_ATTACK_WINDOW_MINUTES,
    CONF_COUNTRY_ALLOW,
    CONF_COUNTRY_DENY,
    CONF_ESCALATION,
    CONF_NETWORK_OVERRIDES,
    CONF_THRESHOLD,
    CONF_WINDOW_MINUTES,
    DEFAULT_OPTIONS,
)
from .iputil import IPNetwork, NetworkSet, parse_network

_DURATION_RE = re.compile(r"^(\d+)\s*([smhdw])$")
_UNITS = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}
_PERMANENT = {"permanent", "perm", "forever", "0", "never"}
_COUNTRY_RE = re.compile(r"^[A-Z]{2}$")


class SettingsError(ValueError):
    """Invalid setting. `key` is a translation key for the error."""

    def __init__(self, key: str, detail: str = "") -> None:
        """Init."""
        super().__init__(detail or key)
        self.key = key
        self.detail = detail


def parse_duration(text: str) -> timedelta | None:
    """Parse '1h', '30m', '7d' or 'permanent' (None)."""
    value = text.strip().lower()
    if value in _PERMANENT:
        return None
    match = _DURATION_RE.match(value)
    if not match:
        raise SettingsError("invalid_duration", text)
    amount = int(match.group(1))
    if amount <= 0:
        raise SettingsError("invalid_duration", text)
    return timedelta(seconds=amount * _UNITS[match.group(2)])


def parse_escalation(text: str) -> list[timedelta | None]:
    """Parse a comma separated escalation ladder."""
    steps = [part for part in re.split(r"[,\s]+", text.strip()) if part]
    if not steps:
        raise SettingsError("invalid_escalation", text)
    ladder = [parse_duration(step) for step in steps]
    for step in ladder[:-1]:
        if step is None:
            raise SettingsError("invalid_escalation", "permanent must be last")
    return ladder


@dataclass(frozen=True, slots=True)
class Override:
    """Per-network threshold override. threshold 0 disables protection."""

    network: IPNetwork
    threshold: int
    window: timedelta


def parse_overrides(text: str) -> list[Override]:
    """Parse lines of `CIDR: threshold/window_minutes` or `CIDR: off`."""
    result: list[Override] = []
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        net_text, sep, rule = line.rpartition(" ")
        if not sep:
            raise SettingsError("invalid_override", raw)
        net_text = net_text.strip().rstrip(":").strip()
        rule = rule.strip().lower()
        try:
            network = parse_network(net_text)
        except ValueError as err:
            raise SettingsError("invalid_override", raw) from err
        if rule == "off":
            result.append(Override(network, 0, timedelta(minutes=1)))
            continue
        threshold_text, slash, window_text = rule.partition("/")
        try:
            threshold = int(threshold_text)
            window = int(window_text) if slash else 0
        except ValueError as err:
            raise SettingsError("invalid_override", raw) from err
        if threshold < 1 or (slash and window < 1):
            raise SettingsError("invalid_override", raw)
        result.append(
            Override(network, threshold, timedelta(minutes=window) if window else timedelta(0))
        )
    return result


def parse_countries(text: str) -> frozenset[str]:
    """Parse a comma separated list of ISO 3166-1 alpha-2 codes."""
    codes = {part.strip().upper() for part in re.split(r"[,\s]+", text) if part.strip()}
    for code in codes:
        if not _COUNTRY_RE.match(code):
            raise SettingsError("invalid_country", code)
    return frozenset(codes)


@dataclass(frozen=True, slots=True)
class ProtectionSettings:
    """Effective failed-login protection settings."""

    threshold: int
    window: timedelta
    ladder: list[timedelta | None]
    overrides: list[Override]
    attack_threshold: int
    attack_window: timedelta

    def rule_for(self, addr: Any) -> tuple[int, timedelta]:
        """Return (threshold, window) for an address, most specific override wins."""
        best: Override | None = None
        for override in self.overrides:
            if (
                addr.version == override.network.version
                and addr in override.network
                and (best is None or override.network.prefixlen > best.network.prefixlen)
            ):
                best = override
        if best is None:
            return self.threshold, self.window
        return best.threshold, best.window or self.window

    def duration_for(self, offense: int) -> timedelta | None:
        """Ban duration for the n-th offense (1-based)."""
        index = min(max(offense, 1), len(self.ladder)) - 1
        return self.ladder[index]


def merged(options: Mapping[str, Any]) -> dict[str, Any]:
    """Return options merged over defaults."""
    data = dict(DEFAULT_OPTIONS)
    data.update(options)
    return data


def protection_settings(options: Mapping[str, Any]) -> ProtectionSettings:
    """Build ProtectionSettings from options (raises SettingsError)."""
    opts = merged(options)
    threshold = int(opts[CONF_THRESHOLD])
    window = int(opts[CONF_WINDOW_MINUTES])
    if threshold < 1:
        raise SettingsError("invalid_threshold")
    if window < 1:
        raise SettingsError("invalid_window")
    return ProtectionSettings(
        threshold=threshold,
        window=timedelta(minutes=window),
        ladder=parse_escalation(str(opts[CONF_ESCALATION])),
        overrides=parse_overrides(str(opts[CONF_NETWORK_OVERRIDES])),
        attack_threshold=max(1, int(opts[CONF_ATTACK_THRESHOLD])),
        attack_window=timedelta(minutes=max(1, int(opts[CONF_ATTACK_WINDOW_MINUTES]))),
    )


def country_rules(options: Mapping[str, Any]) -> tuple[frozenset[str], frozenset[str]]:
    """Return (allow, deny) country sets."""
    opts = merged(options)
    allow = parse_countries(str(opts[CONF_COUNTRY_ALLOW]))
    deny = parse_countries(str(opts[CONF_COUNTRY_DENY]))
    if allow & deny:
        raise SettingsError("country_conflict", ", ".join(sorted(allow & deny)))
    return allow, deny


def override_networks(overrides: list[Override]) -> NetworkSet:
    """Networks with protection turned off."""
    return NetworkSet(o.network for o in overrides if o.threshold == 0)
