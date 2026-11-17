"""IP address helpers: parsing, matching and sanitising request data."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
import ipaddress
import re

from .const import MAX_PATH_LENGTH, MAX_USER_AGENT_LENGTH

type IPAddress = ipaddress.IPv4Address | ipaddress.IPv6Address
type IPNetwork = ipaddress.IPv4Network | ipaddress.IPv6Network

_HOSTNAME_RE = re.compile(
    r"^(?=.{1,253}$)(?!-)[A-Za-z0-9-]{1,63}(?<!-)(\.(?!-)[A-Za-z0-9-]{1,63}(?<!-))*\.?$"
)
# Path segments that carry secrets in Home Assistant URLs.
_SECRET_PREFIXES = (
    "/api/webhook/",
    "/api/hassio_ingress/",
    "/api/ingress/",
    "/auth/authorize/",
)
_TOKENISH_RE = re.compile(r"^[A-Za-z0-9_\-.~%]{24,}$")


class InvalidTargetError(ValueError):
    """Raised when a string is not an IP address or network."""


def normalize_address(addr: IPAddress) -> IPAddress:
    """Map IPv4-mapped IPv6 addresses to plain IPv4."""
    if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped is not None:
        return addr.ipv4_mapped
    return addr


def parse_address(value: str) -> IPAddress:
    """Parse a single IP address, raising InvalidTargetError."""
    try:
        return normalize_address(ipaddress.ip_address(value.strip()))
    except ValueError as err:
        raise InvalidTargetError(f"Not an IP address: {value!r}") from err


def parse_network(value: str) -> IPNetwork:
    """Parse an IP or CIDR into a network. Host bits must be zero."""
    text = value.strip()
    if not text:
        raise InvalidTargetError("Empty address")
    try:
        if "/" not in text:
            addr = parse_address(text)
            return ipaddress.ip_network(addr)
        net = ipaddress.ip_network(text, strict=True)
    except ValueError as err:
        raise InvalidTargetError(f"Not an IP address or CIDR range: {value!r}") from err
    if isinstance(net, ipaddress.IPv6Network) and net.prefixlen >= 96:
        mapped = net.network_address.ipv4_mapped
        if mapped is not None:
            return ipaddress.ip_network(f"{mapped}/{net.prefixlen - 96}")
    return net


def is_single(net: IPNetwork) -> bool:
    """Return True if the network is a single host."""
    return net.prefixlen == net.max_prefixlen


def network_key(net: IPNetwork) -> str:
    """Canonical string for a network: plain IP for single hosts."""
    return str(net.network_address) if is_single(net) else str(net)


def is_hostname(value: str) -> bool:
    """Return True if value looks like a DNS hostname (not an IP)."""
    text = value.strip()
    if not text or not _HOSTNAME_RE.match(text):
        return False
    try:
        parse_network(text)
    except InvalidTargetError:
        return any(c.isalpha() for c in text)
    return False


def overlaps(net: IPNetwork, others: Iterable[IPNetwork]) -> list[IPNetwork]:
    """Return the networks in `others` that overlap `net`."""
    return [other for other in others if other.version == net.version and net.overlaps(other)]


def is_public(addr: IPAddress) -> bool:
    """Return True for globally routable addresses."""
    return bool(addr.is_global) and not addr.is_multicast


def sanitize_path(path: str) -> str:
    """Return a request path that is safe to store.

    Query strings are dropped by the caller (we only ever receive `request.path`),
    secret-bearing segments are replaced and the result is length-bounded.
    """
    path = path.split("?", 1)[0].split("#", 1)[0]
    for prefix in _SECRET_PREFIXES:
        if path.startswith(prefix):
            return prefix + "<redacted>"
    parts = ["<redacted>" if _TOKENISH_RE.match(part) else part for part in path.split("/")]
    clean = "/".join(parts)
    return clean[:MAX_PATH_LENGTH]


def sanitize_user_agent(user_agent: str | None) -> str | None:
    """Bound and strip control characters from a user agent."""
    if not user_agent:
        return None
    clean = "".join(ch for ch in user_agent if ch.isprintable())
    return clean[:MAX_USER_AGENT_LENGTH]


class NetworkSet:
    """Fast membership test for a set of networks.

    Networks are grouped by prefix length so a lookup costs one dict probe
    per distinct prefix length rather than a scan over every network.
    """

    def __init__(self, networks: Iterable[IPNetwork] = ()) -> None:
        """Build the set."""
        self._by_prefix: dict[tuple[int, int], dict[int, IPNetwork]] = {}
        for net in networks:
            self.add(net)

    def add(self, net: IPNetwork) -> None:
        """Add a network."""
        key = (net.version, net.prefixlen)
        self._by_prefix.setdefault(key, {})[int(net.network_address)] = net

    def match(self, addr: IPAddress) -> IPNetwork | None:
        """Return the most specific network containing addr."""
        addr = normalize_address(addr)
        best: IPNetwork | None = None
        value = int(addr)
        bits = addr.max_prefixlen
        for (version, prefix), nets in self._by_prefix.items():
            if version != addr.version:
                continue
            masked = (value >> (bits - prefix)) << (bits - prefix) if prefix else 0
            found = nets.get(masked)
            if found is not None and (best is None or found.prefixlen > best.prefixlen):
                best = found
        return best

    def __contains__(self, addr: object) -> bool:
        """Return True if addr is inside any network."""
        if not isinstance(addr, (ipaddress.IPv4Address, ipaddress.IPv6Address)):
            return False
        return self.match(addr) is not None

    def __len__(self) -> int:
        """Return the number of networks."""
        return sum(len(nets) for nets in self._by_prefix.values())

    def __iter__(self) -> Iterator[IPNetwork]:
        """Iterate networks."""
        for nets in self._by_prefix.values():
            yield from nets.values()
