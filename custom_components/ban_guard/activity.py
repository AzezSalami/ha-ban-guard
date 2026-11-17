"""Bounded activity log kept in `.storage`."""

from __future__ import annotations

from collections import Counter, deque
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import (
    ACT_BAN,
    ACT_BLOCKED,
    ACT_FAILED_LOGIN,
    ACT_LOGIN,
    STORAGE_KEY_ACTIVITY,
    STORAGE_VERSION,
)
from .models import Activity

SAVE_DELAY = 30


class ActivityLog:
    """In-memory ring buffer persisted with a delayed save."""

    def __init__(self, hass: HomeAssistant, max_entries: int, retention_days: int) -> None:
        """Init."""
        self.hass = hass
        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, STORAGE_KEY_ACTIVITY, private=True
        )
        self.max_entries = max(100, max_entries)
        self.retention = timedelta(days=max(1, retention_days))
        self._entries: deque[Activity] = deque(maxlen=self.max_entries)
        self._next_id = 1
        self._listeners: list[Callable[[Activity], None]] = []

    async def async_load(self) -> None:
        """Load from storage."""
        data = await self._store.async_load() or {}
        for raw in data.get("entries", []):
            try:
                self._entries.append(Activity.from_dict(raw))
            except (KeyError, ValueError, TypeError):
                continue
        self._next_id = int(data.get("next_id", 0)) or (
            max((e.id for e in self._entries), default=0) + 1
        )
        self.purge()

    def _data(self) -> dict[str, Any]:
        return {
            "next_id": self._next_id,
            "entries": [e.as_dict() for e in self._entries],
        }

    async def async_save_now(self) -> None:
        """Flush to disk."""
        await self._store.async_save(self._data())

    def configure(self, max_entries: int, retention_days: int) -> None:
        """Apply new limits."""
        self.max_entries = max(100, max_entries)
        self.retention = timedelta(days=max(1, retention_days))
        self._entries = deque(self._entries, maxlen=self.max_entries)
        self.purge()

    @callback
    def add(
        self,
        type_: str,
        ip: str,
        *,
        path: str | None = None,
        user_agent: str | None = None,
        detail: str | None = None,
        user: str | None = None,
    ) -> Activity:
        """Append an entry and schedule a save."""
        entry = Activity(
            id=self._next_id,
            ts=dt_util.utcnow(),
            type=type_,
            ip=ip,
            path=path,
            user_agent=user_agent,
            detail=detail,
            user=user,
        )
        self._next_id += 1
        self._entries.append(entry)
        self._store.async_delay_save(self._data, SAVE_DELAY)
        for listener in list(self._listeners):
            listener(entry)
        return entry

    @callback
    def subscribe(self, listener: Callable[[Activity], None]) -> Callable[[], None]:
        """Subscribe to new entries."""
        self._listeners.append(listener)

        @callback
        def _remove() -> None:
            if listener in self._listeners:
                self._listeners.remove(listener)

        return _remove

    @callback
    def purge(self) -> int:
        """Drop entries older than the retention period."""
        cutoff = dt_util.utcnow() - self.retention
        removed = 0
        while self._entries and self._entries[0].ts < cutoff:
            self._entries.popleft()
            removed += 1
        if removed:
            self._store.async_delay_save(self._data, SAVE_DELAY)
        return removed

    def entries(
        self,
        *,
        limit: int = 200,
        before_id: int | None = None,
        ip: str | None = None,
        types: set[str] | None = None,
    ) -> list[Activity]:
        """Newest-first entries with optional filters."""
        result: list[Activity] = []
        for entry in reversed(self._entries):
            if before_id is not None and entry.id >= before_id:
                continue
            if ip is not None and entry.ip != ip:
                continue
            if types is not None and entry.type not in types:
                continue
            result.append(entry)
            if len(result) >= limit:
                break
        return result

    def count_since(self, type_: str, since: datetime) -> int:
        """Count entries of a type since a time."""
        count = 0
        for entry in reversed(self._entries):
            if entry.ts < since:
                break
            if entry.type == type_:
                count += 1
        return count

    def stats(self, country_of: Callable[[str], str | None]) -> dict[str, Any]:
        """Overview statistics."""
        now = dt_util.utcnow()
        today = dt_util.as_local(now).date()
        days = [(today - timedelta(days=offset)).isoformat() for offset in range(6, -1, -1)]
        per_day = dict.fromkeys(days, 0)
        week_ago = now - timedelta(days=7)
        offenders: Counter[str] = Counter()
        countries: Counter[str] = Counter()
        for entry in reversed(self._entries):
            if entry.ts < week_ago:
                break
            if entry.type == ACT_FAILED_LOGIN:
                day = dt_util.as_local(entry.ts).date().isoformat()
                if day in per_day:
                    per_day[day] += 1
            if entry.type in (ACT_FAILED_LOGIN, ACT_BLOCKED):
                offenders[entry.ip] += 1
                if (country := country_of(entry.ip)) is not None:
                    countries[country] += 1
        day_ago = now - timedelta(days=1)
        return {
            "failed_logins_24h": self.count_since(ACT_FAILED_LOGIN, day_ago),
            "bans_24h": self.count_since(ACT_BAN, day_ago),
            "blocked_24h": self.count_since(ACT_BLOCKED, day_ago),
            "logins_24h": self.count_since(ACT_LOGIN, day_ago),
            "failed_logins_7d": [{"date": d, "count": c} for d, c in per_day.items()],
            "top_ips": [{"ip": ip, "count": c} for ip, c in offenders.most_common(10)],
            "top_countries": [{"country": cc, "count": c} for cc, c in countries.most_common(10)],
        }

    def __len__(self) -> int:
        """Number of entries."""
        return len(self._entries)
