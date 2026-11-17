"""Data models for Ban Guard."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any

from homeassistant.util import dt as dt_util

from .iputil import IPNetwork, is_single, network_key, parse_network


def _parse_dt(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return dt_util.as_utc(value)
    parsed = dt_util.parse_datetime(str(value))
    if parsed is None:
        raise ValueError(f"Invalid datetime: {value!r}")
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt_util.UTC)
    return dt_util.as_utc(parsed)


def _fmt_dt(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


@dataclass(slots=True)
class Ban:
    """A ban on an IP address or network."""

    network: IPNetwork
    reason: str
    source: str
    created_by: str | None
    created_at: datetime
    expires_at: datetime | None = None
    offense: int = 0

    @property
    def key(self) -> str:
        """Canonical identifier."""
        return network_key(self.network)

    @property
    def single(self) -> bool:
        """True if this ban covers a single address."""
        return is_single(self.network)

    @property
    def permanent(self) -> bool:
        """True if the ban never expires."""
        return self.expires_at is None

    def expired(self, now: datetime) -> bool:
        """Return True if the ban has expired."""
        return self.expires_at is not None and self.expires_at <= now

    def as_dict(self) -> dict[str, Any]:
        """Serialise."""
        return {
            "ip": self.key,
            "reason": self.reason,
            "source": self.source,
            "created_by": self.created_by,
            "created_at": _fmt_dt(self.created_at),
            "expires_at": _fmt_dt(self.expires_at),
            "offense": self.offense,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Ban:
        """Deserialise."""
        created = _parse_dt(data.get("created_at")) or dt_util.utcnow()
        return cls(
            network=parse_network(str(data["ip"])),
            reason=str(data.get("reason") or ""),
            source=str(data.get("source") or "manual"),
            created_by=data.get("created_by"),
            created_at=created,
            expires_at=_parse_dt(data.get("expires_at")),
            offense=int(data.get("offense") or 0),
        )


@dataclass(slots=True)
class AllowEntry:
    """An allowlist entry: IP, CIDR or hostname."""

    value: str
    comment: str
    created_by: str | None
    created_at: datetime
    resolved: list[str] = field(default_factory=list)
    resolved_at: datetime | None = None

    @property
    def is_hostname(self) -> bool:
        """True if the entry is a hostname."""
        try:
            parse_network(self.value)
        except ValueError:
            return True
        return False

    def networks(self) -> list[IPNetwork]:
        """Return all networks this entry currently covers."""
        if not self.is_hostname:
            return [parse_network(self.value)]
        nets: list[IPNetwork] = []
        for addr in self.resolved:
            try:
                nets.append(parse_network(addr))
            except ValueError:
                continue
        return nets

    def as_dict(self) -> dict[str, Any]:
        """Serialise."""
        return {
            "value": self.value,
            "comment": self.comment,
            "created_by": self.created_by,
            "created_at": _fmt_dt(self.created_at),
            "resolved": list(self.resolved),
            "resolved_at": _fmt_dt(self.resolved_at),
            "hostname": self.is_hostname,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AllowEntry:
        """Deserialise."""
        return cls(
            value=str(data["value"]).strip().lower(),
            comment=str(data.get("comment") or ""),
            created_by=data.get("created_by"),
            created_at=_parse_dt(data.get("created_at")) or dt_util.utcnow(),
            resolved=[str(x) for x in data.get("resolved") or []],
            resolved_at=_parse_dt(data.get("resolved_at")),
        )


@dataclass(slots=True)
class Offense:
    """Escalation state for one address."""

    count: int
    last: datetime

    def as_dict(self) -> dict[str, Any]:
        """Serialise."""
        return {"count": self.count, "last": _fmt_dt(self.last)}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Offense:
        """Deserialise."""
        return cls(int(data["count"]), _parse_dt(data["last"]) or dt_util.utcnow())


@dataclass(slots=True)
class Activity:
    """One activity log entry."""

    id: int
    ts: datetime
    type: str
    ip: str
    path: str | None = None
    user_agent: str | None = None
    detail: str | None = None
    user: str | None = None

    def as_dict(self) -> dict[str, Any]:
        """Serialise."""
        data = asdict(self)
        data["ts"] = _fmt_dt(self.ts)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Activity:
        """Deserialise."""
        return cls(
            id=int(data["id"]),
            ts=_parse_dt(data["ts"]) or dt_util.utcnow(),
            type=str(data["type"]),
            ip=str(data["ip"]),
            path=data.get("path"),
            user_agent=data.get("user_agent"),
            detail=data.get("detail"),
            user=data.get("user"),
        )


def parse_datetime_value(value: Any) -> datetime | None:
    """Public wrapper for datetime parsing."""
    return _parse_dt(value)
