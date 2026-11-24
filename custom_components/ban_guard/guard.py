"""Lockout guard: addresses that must never be banned."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import timedelta
import ipaddress
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.hassio import get_supervisor_ip, is_hassio
from homeassistant.util import dt as dt_util

from .const import SUPERVISOR_NETWORK
from .iputil import IPAddress, IPNetwork, normalize_address, parse_network

_LOGGER = logging.getLogger(__name__)

ADMIN_IP_MAX_AGE = timedelta(days=1)

_ALWAYS: tuple[tuple[str, str], ...] = (
    ("127.0.0.0/8", "loopback"),
    ("::1/128", "loopback"),
    ("0.0.0.0/32", "unspecified"),
    ("::/128", "unspecified"),
)


@dataclass(frozen=True, slots=True)
class Protected:
    """A protected network and why it is protected."""

    network: IPNetwork
    reason: str  # translation key suffix: loopback, host, supervisor, admin, proxy


class LockoutGuard:
    """Keep track of networks that may never be banned."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Init."""
        self.hass = hass
        self._static: list[Protected] = [
            Protected(ipaddress.ip_network(net), reason) for net, reason in _ALWAYS
        ]
        self._host: list[Protected] = []
        self._admin: list[IPAddress] = []

    async def async_refresh(self) -> None:
        """Refresh the HA host's own addresses and Supervisor network."""
        host: list[Protected] = []
        try:
            from homeassistant.components import network  # noqa: PLC0415

            for adapter in await network.async_get_adapters(self.hass):
                for ipv4 in adapter["ipv4"]:
                    host.append(_host(ipv4["address"], "host"))
                for ipv6 in adapter["ipv6"]:
                    host.append(_host(ipv6["address"], "host"))
        except Exception:
            _LOGGER.debug("Could not read network adapters", exc_info=True)
        api = getattr(self.hass.config, "api", None)
        if api is not None and getattr(api, "local_ip", None):
            host.append(_host(api.local_ip, "host"))
        if is_hassio(self.hass):
            host.append(Protected(ipaddress.ip_network(SUPERVISOR_NETWORK), "supervisor"))
            if (sup := get_supervisor_ip()) is not None:
                host.append(_host(sup, "supervisor"))
        http = getattr(self.hass, "http", None)
        for proxy in getattr(http, "trusted_proxies", None) or []:
            try:
                host.append(Protected(parse_network(str(proxy)), "proxy"))
            except ValueError:
                continue
        self._host = [p for p in host if p.network.prefixlen > 0]

    def admin_ips(self) -> list[IPAddress]:
        """Return IPs recently used by admin users (cached)."""
        return list(self._admin)

    async def async_refresh_admins(self) -> None:
        """Cache IPs recently used by active admin users' refresh tokens."""
        result: list[IPAddress] = []
        cutoff = dt_util.utcnow() - ADMIN_IP_MAX_AGE
        try:
            users = await self.hass.auth.async_get_users()
        except Exception:
            _LOGGER.debug("Could not read users", exc_info=True)
            return
        for user in users:
            if not user.is_admin or not user.is_active or user.system_generated:
                continue
            for token in user.refresh_tokens.values():
                if not token.last_used_ip or (
                    token.last_used_at is not None and token.last_used_at < cutoff
                ):
                    continue
                try:
                    result.append(normalize_address(ipaddress.ip_address(token.last_used_ip)))
                except ValueError:
                    continue
        self._admin = result

    def protected(self, requester: IPAddress | None = None) -> list[Protected]:
        """Return all protected networks."""
        items = list(self._static) + list(self._host)
        for addr in self.admin_ips():
            items.append(Protected(ipaddress.ip_network(addr), "admin"))
        if requester is not None:
            items.append(Protected(ipaddress.ip_network(normalize_address(requester)), "current"))
        return items

    def conflicts(self, network: IPNetwork, requester: IPAddress | None = None) -> list[Protected]:
        """Return protected entries that a ban on `network` would cover."""
        return [
            p
            for p in self.protected(requester)
            if p.network.version == network.version and network.overlaps(p.network)
        ]

    def protection_for(self, addr: IPAddress) -> Protected | None:
        """Return the most specific protection covering a single address."""
        addr = normalize_address(addr)
        best: Protected | None = None
        for p in self.protected():
            if (
                p.network.version == addr.version
                and addr in p.network
                and (best is None or p.network.prefixlen > best.network.prefixlen)
            ):
                best = p
        return best

    def is_protected(self, addr: IPAddress, extra: Iterable[IPAddress] = ()) -> bool:
        """Return True if a single address is protected."""
        addr = normalize_address(addr)
        if addr in extra:
            return True
        return self.protection_for(addr) is not None


def _host(address: str, reason: str) -> Protected:
    addr = normalize_address(ipaddress.ip_address(address.split("%", 1)[0]))
    return Protected(ipaddress.ip_network(addr), reason)
