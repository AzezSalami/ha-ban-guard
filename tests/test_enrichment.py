"""MMDB reader, GeoIP manager, resolver, NPM client and country rules."""

from __future__ import annotations

import gzip
import ipaddress
import os
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.ban_guard import enrichment
from custom_components.ban_guard.const import SOURCE_MANUAL
from custom_components.ban_guard.enrichment import GeoIP, GeoIPError, Resolver
from custom_components.ban_guard.manager import BanGuardManager
from custom_components.ban_guard.mmdb import InvalidDatabaseError, Reader
from custom_components.ban_guard.npm import NPMClient, NPMError, async_detect_addon
from homeassistant.components.http import ban as ha_ban
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .mmdb_writer import build, encode, pointer

DE = {
    "country": {"iso_code": "DE", "names": {"en": "Germany"}},
    "city": {"names": {"en": "Berlin"}},
}
US = {"country": {"iso_code": "US", "names": {"en": "United States"}}}


def urls(edition: str) -> tuple[str, str]:
    from datetime import timedelta

    now = dt_util.utcnow()
    previous = (now.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
    base = f"https://download.db-ip.com/free/dbip-{edition}-lite-"
    return f"{base}{now.strftime('%Y-%m')}.mmdb.gz", f"{base}{previous}.mmdb.gz"


def sample_db(**kwargs: Any) -> bytes:
    return build([("8.8.8.0/24", US), ("85.214.0.0/15", DE), ("2a01:4f8::/32", DE)], **kwargs)


@pytest.mark.parametrize("record_size", [24, 28, 32])
@pytest.mark.parametrize("ip_version", [4, 6])
def test_reader(record_size: int, ip_version: int) -> None:
    entries = [("8.8.8.0/24", US), ("85.214.0.0/15", DE)]
    if ip_version == 6:
        entries.append(("2a01:4f8::/32", DE))
    reader = Reader(build(entries, ip_version=ip_version, record_size=record_size))
    assert reader.get("8.8.8.8")["country"]["iso_code"] == "US"
    assert reader.get("85.215.1.1")["city"]["names"]["en"] == "Berlin"
    assert reader.get("1.1.1.1") is None
    if ip_version == 6:
        assert reader.get("2a01:4f8::1")["country"]["iso_code"] == "DE"
    else:
        assert reader.get("2a01:4f8::1") is None
    assert reader.database_type == "DBIP-Country-Lite"
    assert reader.build_epoch == 2**40


def test_reader_all_types_and_pointers() -> None:
    shared = encode("Shared")
    big = "x" * 300
    record = {
        "name": "y" * 70000,
        "medium": big,
        "f64": 1.5,
        "bytes": b"\x01\x02",
        "u16": 7,
        "u32": 70000,
        "u64": 2**40,
        "u128": 2**70,
        "i32": -5,
        "list": [1, "a"],
        "flag": True,
    }
    raw = encode(record)[: -0 or None]
    db = build([("1.2.3.0/24", record)], ip_version=4, shared_prefix=shared)
    reader = Reader(db)
    value = reader.get("1.2.3.4")
    assert value == record
    # Float32 and pointers decode via the low-level decoder.
    from custom_components.ban_guard.mmdb import _Decoder

    buf = b"\x00" * 4 + bytes([0x00, 15 - 7 | 0]) + b""
    dec = _Decoder(bytes([4, 8]) + b"\x3f\xc0\x00\x00", 0)
    assert dec.decode(0)[0] == pytest.approx(1.5)
    for offset in (5, 3000, 600000, 140000000):
        data = pointer(offset)
        target = bytearray(offset + 1 + 10)
        target[offset : offset + 2] = encode("p")
        payload = bytes(target[: offset + 2]) + data
        dec = _Decoder(payload, 0)
        assert dec.decode(offset + 2)[0] == "p"
    assert raw and buf is not None


def test_reader_rejects_garbage() -> None:
    with pytest.raises(InvalidDatabaseError):
        Reader(b"not a database")
    with pytest.raises(InvalidDatabaseError):
        Reader(b"\x00" * 16 + b"\xab\xcd\xefMaxMind.com" + encode("x"))
    with pytest.raises(InvalidDatabaseError):
        Reader(b"\xab\xcd\xefMaxMind.com" + encode({"node_count": 1}))
    marker = b"\xab\xcd\xefMaxMind.com"
    with pytest.raises(InvalidDatabaseError):
        Reader(marker + encode({"node_count": 0, "record_size": 20, "ip_version": 4}))
    # A tree that loops forever never resolves to data.
    looping = bytes([0, 0, 1, 0, 0, 1]) + bytes([0, 0, 0, 0, 0, 0]) + b"\x00" * 16
    meta = encode({"node_count": 2, "record_size": 24, "ip_version": 4})
    with pytest.raises(InvalidDatabaseError):
        Reader(looping + marker + meta).get("0.0.0.1")
    # A record pointing past the end of the file.
    dangling = (2 + 16 + 5000).to_bytes(3, "big") * 2 + b"\x00" * 16
    meta = encode({"node_count": 1, "record_size": 24, "ip_version": 4})
    with pytest.raises(InvalidDatabaseError):
        Reader(dangling + marker + meta).get("1.1.1.1")
    from custom_components.ban_guard.mmdb import _Decoder

    with pytest.raises(InvalidDatabaseError):
        _Decoder(bytes([0x00, 0x09]), 0).decode(0)  # unknown type 16
    with pytest.raises(InvalidDatabaseError):
        _Decoder(b"", 0).decode(0)


async def test_geoip_download_and_lookup(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, tmp_path: Any
) -> None:
    hass.config.config_dir = str(tmp_path)
    month = dt_util.utcnow().strftime("%Y-%m")
    url = f"https://download.db-ip.com/free/dbip-country-lite-{month}.mmdb.gz"
    aioclient_mock.get(url, content=gzip.compress(sample_db()))
    geo = GeoIP(hass, "country", 10)
    await geo.async_load()
    assert geo.loaded
    assert geo.lookup(ipaddress.ip_address("8.8.8.8")) == {
        "country": "US",
        "country_name": "United States",
        "city": None,
    }
    assert geo.lookup(ipaddress.ip_address("8.8.8.8"))["country"] == "US"  # cached
    assert geo.lookup(ipaddress.ip_address("192.168.1.1")) is None
    assert geo.lookup(ipaddress.ip_address("1.1.1.1")) is None
    # Fresh file: no second download.
    await geo.async_refresh_if_stale()
    assert aioclient_mock.call_count == 1
    await hass.async_add_executor_job(geo.remove_files)
    assert not os.path.exists(geo.path)


async def test_geoip_falls_back_to_previous_month(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, tmp_path: Any
) -> None:
    hass.config.config_dir = str(tmp_path)
    current, previous = urls("city")
    aioclient_mock.get(current, status=404)
    aioclient_mock.get(previous, content=gzip.compress(sample_db()))
    geo = GeoIP(hass, "city", 10)
    await geo.async_download()
    assert aioclient_mock.call_count == 2


@pytest.mark.parametrize(
    ("content", "max_mb"),
    [(b"not gzip", 10), (gzip.compress(b"x" * 100), 10), (gzip.compress(b"\0" * (2 << 20)), 1)],
)
async def test_geoip_bad_downloads(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    tmp_path: Any,
    content: bytes,
    max_mb: int,
) -> None:
    hass.config.config_dir = str(tmp_path)
    for url in urls("country"):
        aioclient_mock.get(url, content=content)
    geo = GeoIP(hass, "country", max_mb)
    with pytest.raises(GeoIPError):
        await geo.async_load()
    assert geo.last_error


async def test_geoip_size_cap_on_download(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, tmp_path: Any
) -> None:
    hass.config.config_dir = str(tmp_path)
    for url in urls("country"):
        aioclient_mock.get(url, content=os.urandom(2 << 20))
    geo = GeoIP(hass, "country", 1)
    with pytest.raises(GeoIPError):
        await geo.async_download()


async def test_geoip_network_error_keeps_existing(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, tmp_path: Any
) -> None:
    hass.config.config_dir = str(tmp_path)
    geo = GeoIP(hass, "country", 10)
    os.makedirs(geo.directory)
    with open(geo.path, "wb") as fh:
        fh.write(sample_db())
    os.utime(geo.path, (0, 0))  # very old
    for url in urls("country"):
        aioclient_mock.get(url, exc=aiohttp.ClientError())
    await geo.async_load()  # refresh fails, old file still used
    assert geo.loaded
    with pytest.raises(GeoIPError):
        await geo.async_refresh_if_stale()
    with open(geo.path, "wb") as fh:
        fh.write(b"corrupt")
    os.utime(geo.path, None)
    with pytest.raises(GeoIPError):
        await geo.async_load()
    with open(geo.path, "wb") as fh:
        fh.write(sample_db())
    geo.max_bytes = 10
    with pytest.raises(GeoIPError):
        await geo.async_load()


@pytest.mark.parametrize(
    "options",
    [{"geoip_enabled": True, "country_deny": "US", "country_allow": ""}],
)
async def test_country_rules(
    hass: HomeAssistant, options: dict[str, Any], http: None, tmp_path: Any
) -> None:
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    geo_dir = os.path.join(hass.config.config_dir, "ban_guard")
    os.makedirs(geo_dir, exist_ok=True)
    with open(os.path.join(geo_dir, "dbip-country-lite.mmdb"), "wb") as fh:
        fh.write(sample_db())
    entry = MockConfigEntry(domain="ban_guard", data={}, options=options)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done(wait_background_tasks=True)
    manager: BanGuardManager = entry.runtime_data
    assert manager.status()["geoip"]["loaded"]
    table = hass.http.app[ha_ban.KEY_BAN_MANAGER].ip_bans_lookup
    assert ipaddress.ip_address("8.8.8.8") in table
    assert ipaddress.ip_address("85.214.1.1") not in table
    assert manager.country_of("8.8.8.8") == "US"
    assert manager.country_of("bogus") is None
    assert manager.geo("bogus") is None
    await manager.async_ban("85.214.1.1", source=SOURCE_MANUAL, user=None)
    view = manager.ban_view(manager.bans["85.214.1.1"])
    assert view["country"] == "DE" and view["city"] == "Berlin"
    manager.country_deny = frozenset()
    manager.country_allow = frozenset({"DE"})
    assert ipaddress.ip_address("8.8.8.8") in table
    await manager._async_geoip_tick(None)  # type: ignore[arg-type]


@pytest.mark.parametrize("options", [{"geoip_enabled": True}])
async def test_geoip_failure_raises_issue(
    hass: HomeAssistant, options: dict[str, Any], http: None, aioclient_mock: AiohttpClientMocker
) -> None:
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from homeassistant.helpers import issue_registry as ir

    for url in urls("country"):
        aioclient_mock.get(url, status=500)
    entry = MockConfigEntry(domain="ban_guard", data={}, options=options)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert ir.async_get(hass).async_get_issue("ban_guard", "geoip_failed")
    manager: BanGuardManager = entry.runtime_data
    assert manager.country_of("8.8.8.8") is None
    with patch.object(manager.geoip, "async_refresh_if_stale", side_effect=GeoIPError("x")):
        await manager._async_geoip_tick(None)  # type: ignore[arg-type]


async def test_resolver(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    off = Resolver(hass, rdns=False, doh=False, doh_url="")
    assert await off.async_reverse(ipaddress.ip_address("8.8.8.8")) is None

    local = Resolver(hass, rdns=True, doh=False, doh_url="")
    loop = hass.loop
    with (
        patch.object(loop, "getnameinfo", AsyncMock(return_value=("dns.google", "0"))),
        patch.object(
            loop,
            "getaddrinfo",
            AsyncMock(
                return_value=[(2, 1, 6, "", ("1.2.3.4", 0)), (10, 1, 6, "", ("fe80::1%2", 0, 0, 2))]
            ),
        ),
    ):
        assert await local.async_reverse(ipaddress.ip_address("8.8.8.8")) == "dns.google"
        assert await local.async_resolve("x.example") == ["1.2.3.4", "fe80::1"]
    # cached
    assert await local.async_reverse(ipaddress.ip_address("8.8.8.8")) == "dns.google"
    with patch.object(loop, "getaddrinfo", AsyncMock(side_effect=OSError)):
        assert await local.async_resolve("x.example") == []

    doh = Resolver(hass, rdns=True, doh=True, doh_url="https://dns.example/q")
    aioclient_mock.get(
        "https://dns.example/q",
        json={"Answer": [{"type": 12, "data": "host.example."}, {"type": 1, "data": "9.9.9.9"}]},
    )
    assert await doh.async_reverse(ipaddress.ip_address("9.9.9.9")) == "host.example"
    assert await doh.async_resolve("host.example") == ["9.9.9.9"]
    aioclient_mock.clear_requests()
    aioclient_mock.get("https://dns.example/q", status=500)
    assert await doh.async_reverse(ipaddress.ip_address("9.9.9.8")) is None
    assert await doh.async_resolve("host.example") == []
    assert enrichment._is_ip("1.2.3.4") and not enrichment._is_ip("x")


NPM = "http://npm.local:81"


async def test_npm_client(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    aioclient_mock.post(f"{NPM}/api/tokens", json={"token": "tok"})
    aioclient_mock.get(f"{NPM}/api/nginx/access-lists", json=[{"id": 3, "name": "BG"}])
    aioclient_mock.get(
        f"{NPM}/api/nginx/access-lists/3?expand=items,clients",
        json={"name": "BG", "items": [{"username": "u"}], "satisfy_any": True},
    )
    aioclient_mock.put(f"{NPM}/api/nginx/access-lists/3", json={})
    client = NPMClient(hass, NPM + "/", "a@b.c", "pw", True)
    assert await client.async_access_lists() == [{"id": 3, "name": "BG"}]
    assert await client.async_sync(3, ["1.2.3.4", "10.0.0.0/8", "1.2.3.4"]) == 2
    put = [c for c in aioclient_mock.mock_calls if c[0] == "PUT"][0]
    body = put[2]
    assert body["clients"][-1] == {"address": "all", "directive": "allow"}
    assert body["items"] == [{"username": "u", "password": ""}]
    assert put[3]["authorization"] == "Bearer tok"


@pytest.mark.parametrize(
    ("kwargs", "key"),
    [
        ({"status": 401}, "invalid_auth"),
        ({"status": 404}, "not_found"),
        ({"status": 500}, "cannot_connect"),
        ({"exc": aiohttp.ClientError()}, "cannot_connect"),
        ({"exc": TimeoutError()}, "cannot_connect"),
        ({"json": {}}, "invalid_auth"),
    ],
)
async def test_npm_errors(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, kwargs: dict[str, Any], key: str
) -> None:
    aioclient_mock.post(f"{NPM}/api/tokens", **kwargs)
    client = NPMClient(hass, NPM, "a", "b", False)
    with pytest.raises(NPMError) as err:
        await client.async_access_lists()
    assert err.value.key == key


async def test_npm_unexpected_payloads(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    aioclient_mock.post(f"{NPM}/api/tokens", json={"token": "t"})
    aioclient_mock.get(f"{NPM}/api/nginx/access-lists", json={"oops": 1})
    aioclient_mock.get(f"{NPM}/api/nginx/access-lists/1?expand=items,clients", json=[])
    client = NPMClient(hass, NPM, "a", "b", True)
    with pytest.raises(NPMError):
        await client.async_access_lists()
    with pytest.raises(NPMError):
        await client.async_sync(1, [])


async def test_detect_addon(hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch) -> None:
    assert await async_detect_addon(hass) is None
    hass.config.components.add("hassio")
    addons = [
        {"slug": "core_ssh", "name": "SSH"},
        {"slug": "a0d7b954_nginxproxymanager", "name": "Nginx Proxy Manager", "state": "started"},
    ]
    with patch(
        "homeassistant.components.hassio.get_addons_list",
        MagicMock(return_value=addons),
        create=True,
    ):
        found = await async_detect_addon(hass)
    assert found is not None and found["slug"] == "a0d7b954_nginxproxymanager"
    assert found["suggested_url"] == "http://a0d7b954-nginxproxymanager:81"
    with patch(
        "homeassistant.components.hassio.get_addons_list", MagicMock(return_value=[]), create=True
    ):
        assert await async_detect_addon(hass) is None
    with patch(
        "homeassistant.components.hassio.get_addons_list", side_effect=RuntimeError, create=True
    ):
        assert await async_detect_addon(hass) is None
    from homeassistant.components import hassio

    info = {a["slug"]: a for a in addons}
    monkeypatch.delattr(hassio, "get_addons_list", raising=False)
    with patch("homeassistant.components.hassio.get_addons_info", MagicMock(return_value=info)):
        found = await async_detect_addon(hass)
    assert found is not None and found["name"] == "Nginx Proxy Manager"


async def test_manager_npm_sync(
    hass: HomeAssistant, manager: BanGuardManager, aioclient_mock: AiohttpClientMocker
) -> None:
    from homeassistant.helpers import issue_registry as ir

    secret = await manager.secret.async_encrypt("pw")
    manager.options.update(
        {
            "npm_enabled": True,
            "npm_url": NPM,
            "npm_username": "a",
            "npm_secret": secret,
            "npm_access_list_id": 3,
        }
    )
    aioclient_mock.post(f"{NPM}/api/tokens", json={"token": "t"})
    aioclient_mock.get(f"{NPM}/api/nginx/access-lists/3?expand=items,clients", json={"name": "BG"})
    aioclient_mock.put(f"{NPM}/api/nginx/access-lists/3", json={})
    await manager.async_ban("198.51.100.1", source=SOURCE_MANUAL, user=None)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert manager.npm_status["ok"] is True and manager.npm_status["count"] == 1

    aioclient_mock.clear_requests()
    aioclient_mock.post(f"{NPM}/api/tokens", status=401)
    await manager.async_npm_sync()
    assert manager.npm_status == {"enabled": True, "ok": False, "error": "invalid_auth"}
    assert ir.async_get(hass).async_get_issue("ban_guard", "npm_failed")

    manager.options["npm_secret"] = "garbage"
    await manager.async_npm_sync()
    assert manager.npm_status == {"enabled": True}
    await manager.secret.async_remove()
