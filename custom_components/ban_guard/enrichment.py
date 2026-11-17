"""Optional enrichment: GeoIP (DB-IP Lite), reverse DNS, DNS-over-HTTPS.

Everything here is opt-in and off by default. Outbound calls:
* GeoIP: one HTTPS download per month from download.db-ip.com.
* Reverse DNS: PTR queries to the system resolver.
* DNS-over-HTTPS: PTR / A / AAAA queries to the configured DoH endpoint.
"""

from __future__ import annotations

import asyncio
from collections import OrderedDict
from datetime import datetime, timedelta
import gzip
import io
import ipaddress
import logging
import os
import socket
from typing import Any
import zlib

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import dt as dt_util

from .const import GEOIP_DIRNAME, GEOIP_URL_TEMPLATE
from .iputil import IPAddress, is_public
from .mmdb import InvalidDatabaseError, Reader

_LOGGER = logging.getLogger(__name__)

_CACHE_SIZE = 4096
_DOWNLOAD_TIMEOUT = aiohttp.ClientTimeout(total=600)
_DNS_TIMEOUT = 5.0
_REFRESH_AGE = timedelta(days=30)


class _LRU[K, V]:
    def __init__(self, size: int = _CACHE_SIZE) -> None:
        self._data: OrderedDict[K, V] = OrderedDict()
        self._size = size

    def get(self, key: K) -> V | None:
        if key in self._data:
            self._data.move_to_end(key)
            return self._data[key]
        return None

    def __contains__(self, key: object) -> bool:
        return key in self._data

    def set(self, key: K, value: V) -> None:
        self._data[key] = value
        self._data.move_to_end(key)
        while len(self._data) > self._size:
            self._data.popitem(last=False)

    def clear(self) -> None:
        self._data.clear()


class GeoIPError(Exception):
    """GeoIP download or load failed."""


class GeoIP:
    """DB-IP Lite database manager."""

    def __init__(self, hass: HomeAssistant, edition: str, max_mb: int) -> None:
        """Init."""
        self.hass = hass
        self.edition = edition
        self.max_bytes = max(1, max_mb) * 1024 * 1024
        self.directory = hass.config.path(GEOIP_DIRNAME)
        self.path = os.path.join(self.directory, f"dbip-{edition}-lite.mmdb")
        self._reader: Reader | None = None
        self._cache: _LRU[str, dict[str, Any] | None] = _LRU()
        self.last_error: str | None = None

    @property
    def loaded(self) -> bool:
        """True when a database is in memory."""
        return self._reader is not None

    def _file_age(self) -> timedelta | None:
        try:
            mtime = os.path.getmtime(self.path)
        except OSError:
            return None
        return dt_util.utcnow() - datetime.fromtimestamp(mtime, dt_util.UTC)

    def _load_file(self) -> Reader:
        size = os.path.getsize(self.path)
        if size > self.max_bytes:
            raise GeoIPError(f"Database is {size} bytes, above the size cap")
        with open(self.path, "rb") as fh:
            return Reader(fh.read())

    async def async_load(self) -> None:
        """Load the database from disk, downloading it if needed or stale."""
        age = await self.hass.async_add_executor_job(self._file_age)
        if age is None or age > _REFRESH_AGE:
            try:
                await self.async_download()
            except GeoIPError:
                if age is None:
                    raise
                _LOGGER.warning("GeoIP refresh failed, keeping the existing database")
        try:
            self._reader = await self.hass.async_add_executor_job(self._load_file)
        except (OSError, InvalidDatabaseError) as err:
            raise GeoIPError(str(err)) from err
        self._cache.clear()
        self.last_error = None

    async def async_refresh_if_stale(self) -> None:
        """Monthly refresh."""
        age = await self.hass.async_add_executor_job(self._file_age)
        if age is not None and age <= _REFRESH_AGE:
            return
        await self.async_download()
        self._reader = await self.hass.async_add_executor_job(self._load_file)
        self._cache.clear()

    def _url(self, month: str) -> str:
        return GEOIP_URL_TEMPLATE.format(edition=self.edition, month=month)

    async def async_download(self) -> None:
        """Download this month's (or last month's) database."""
        session = async_get_clientsession(self.hass)
        now = dt_util.utcnow()
        previous = (now.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
        last_err: Exception | None = None
        for month in (now.strftime("%Y-%m"), previous):
            url = self._url(month)
            try:
                async with session.get(url, timeout=_DOWNLOAD_TIMEOUT) as resp:
                    if resp.status == 404:
                        last_err = GeoIPError(f"{url} not found")
                        continue
                    resp.raise_for_status()
                    compressed = bytearray()
                    async for chunk in resp.content.iter_chunked(65536):
                        compressed.extend(chunk)
                        if len(compressed) > self.max_bytes:
                            raise GeoIPError("Download exceeds the size cap")
                await self.hass.async_add_executor_job(self._store, bytes(compressed))
            except (
                aiohttp.ClientError,
                TimeoutError,
                OSError,
                EOFError,
                zlib.error,
                InvalidDatabaseError,
                GeoIPError,
            ) as err:
                last_err = err
                continue
            return
        self.last_error = str(last_err)
        raise GeoIPError(str(last_err))

    def _store(self, compressed: bytes) -> None:
        os.makedirs(self.directory, exist_ok=True)
        out = bytearray()
        with gzip.GzipFile(fileobj=io.BytesIO(compressed)) as gz:
            while chunk := gz.read(1 << 20):
                out.extend(chunk)
                if len(out) > self.max_bytes:
                    raise GeoIPError("Database exceeds the size cap")
        Reader(bytes(out))  # validate before replacing
        tmp = f"{self.path}.tmp"
        with open(tmp, "wb") as fh:
            fh.write(out)
        os.replace(tmp, self.path)

    def lookup(self, addr: IPAddress) -> dict[str, Any] | None:
        """Return {"country": "DE", "country_name": ..., "city": ...} or None."""
        if self._reader is None or not is_public(addr):
            return None
        key = str(addr)
        if key in self._cache:
            return self._cache.get(key)
        try:
            record = self._reader.get(addr)
        except (InvalidDatabaseError, ValueError, IndexError):
            record = None
        result: dict[str, Any] | None = None
        if isinstance(record, dict):
            country = record.get("country") or {}
            city = record.get("city") or {}
            code = country.get("iso_code")
            if code:
                result = {
                    "country": str(code),
                    "country_name": (country.get("names") or {}).get("en"),
                    "city": (city.get("names") or {}).get("en"),
                }
        self._cache.set(key, result)
        return result

    def remove_files(self) -> None:
        """Delete the database (blocking)."""
        for path in (self.path, f"{self.path}.tmp"):
            try:
                os.remove(path)
            except FileNotFoundError:
                continue


def _ptr_name(addr: IPAddress) -> str:
    return addr.reverse_pointer


class Resolver:
    """Reverse DNS (system resolver or DoH) and hostname resolution, cached."""

    def __init__(self, hass: HomeAssistant, *, rdns: bool, doh: bool, doh_url: str) -> None:
        """Init."""
        self.hass = hass
        self.rdns = rdns
        self.doh = doh
        self.doh_url = doh_url
        self._ptr_cache: _LRU[str, str | None] = _LRU()

    async def async_reverse(self, addr: IPAddress) -> str | None:
        """Return the PTR name for an address, if reverse DNS is enabled."""
        if not self.rdns:
            return None
        key = str(addr)
        if key in self._ptr_cache:
            return self._ptr_cache.get(key)
        name: str | None
        try:
            if self.doh:
                answers = await self._doh_query(_ptr_name(addr), "PTR")
                name = answers[0].rstrip(".") if answers else None
            else:
                loop = asyncio.get_running_loop()
                host, _ = await asyncio.wait_for(
                    loop.getnameinfo((key, 0), socket.NI_NAMEREQD), _DNS_TIMEOUT
                )
                name = host
        except Exception:
            _LOGGER.debug("Reverse lookup of %s failed", key, exc_info=True)
            name = None
        self._ptr_cache.set(key, name)
        return name

    async def async_resolve(self, hostname: str) -> list[str]:
        """Resolve a hostname to addresses (system resolver, or DoH if enabled)."""
        if self.doh:
            result: list[str] = []
            for rtype in ("A", "AAAA"):
                try:
                    result.extend(await self._doh_query(hostname, rtype))
                except Exception:
                    _LOGGER.debug("DoH query for %s failed", hostname, exc_info=True)
                    continue
            return sorted({r for r in result if _is_ip(r)})
        loop = asyncio.get_running_loop()
        try:
            infos = await asyncio.wait_for(
                loop.getaddrinfo(hostname, None, type=socket.SOCK_STREAM), _DNS_TIMEOUT
            )
        except Exception:
            _LOGGER.debug("Resolving %s failed", hostname, exc_info=True)
            return []
        return sorted({str(info[4][0]).split("%", 1)[0] for info in infos})

    async def _doh_query(self, name: str, rtype: str) -> list[str]:
        session = async_get_clientsession(self.hass)
        async with session.get(
            self.doh_url,
            params={"name": name, "type": rtype},
            headers={"accept": "application/dns-json"},
            timeout=aiohttp.ClientTimeout(total=_DNS_TIMEOUT),
        ) as resp:
            resp.raise_for_status()
            payload = await resp.json(content_type=None)
        answers = payload.get("Answer") or [] if isinstance(payload, dict) else []
        wanted = {"A": 1, "AAAA": 28, "PTR": 12}[rtype]
        return [str(a["data"]) for a in answers if a.get("type") == wanted and "data" in a]


def _is_ip(value: str) -> bool:
    try:
        ipaddress.ip_address(value)
    except ValueError:
        return False
    return True
