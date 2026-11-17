"""Pure unit tests: IP parsing, settings parsing, models, ip_bans.yaml I/O."""

from __future__ import annotations

from datetime import timedelta
import ipaddress
from pathlib import Path

import pytest

from custom_components.ban_guard import bansfile
from custom_components.ban_guard.iputil import (
    InvalidTargetError,
    NetworkSet,
    is_hostname,
    is_public,
    network_key,
    overlaps,
    parse_address,
    parse_network,
    sanitize_path,
    sanitize_user_agent,
)
from custom_components.ban_guard.models import Activity, AllowEntry, Ban, Offense
from custom_components.ban_guard.settings import (
    SettingsError,
    country_rules,
    override_networks,
    parse_countries,
    parse_duration,
    parse_escalation,
    parse_overrides,
    protection_settings,
)
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util import dt as dt_util


def test_parse_network() -> None:
    assert network_key(parse_network("1.2.3.4")) == "1.2.3.4"
    assert network_key(parse_network("10.0.0.0/8")) == "10.0.0.0/8"
    assert network_key(parse_network("::ffff:1.2.3.4")) == "1.2.3.4"
    assert network_key(parse_network("::ffff:10.0.0.0/104")) == "10.0.0.0/8"
    assert network_key(parse_network("2001:DB8::/32")) == "2001:db8::/32"
    for bad in ("", "1.2.3.4/8", "x", "1.2.3.4/33"):
        with pytest.raises(InvalidTargetError):
            parse_network(bad)
    with pytest.raises(InvalidTargetError):
        parse_address("1.2.3.4/32")


def test_hostnames_and_helpers() -> None:
    assert is_hostname("vpn.example.com")
    assert not is_hostname("1.2.3.4")
    assert not is_hostname("bad host")
    assert not is_hostname("")
    assert is_public(ipaddress.ip_address("8.8.8.8"))
    assert not is_public(ipaddress.ip_address("192.168.1.1"))
    nets = [parse_network("10.0.0.0/8"), parse_network("::/0")]
    assert overlaps(parse_network("10.1.0.0/16"), nets) == [nets[0]]


def test_network_set() -> None:
    nets = NetworkSet([parse_network("10.0.0.0/8"), parse_network("10.1.0.0/16")])
    nets.add(parse_network("2001:db8::/32"))
    nets.add(parse_network("0.0.0.0/0"))
    assert str(nets.match(ipaddress.ip_address("10.1.2.3"))) == "10.1.0.0/16"
    assert str(nets.match(ipaddress.ip_address("10.2.2.3"))) == "10.0.0.0/8"
    assert str(nets.match(ipaddress.ip_address("8.8.8.8"))) == "0.0.0.0/0"
    assert ipaddress.ip_address("2001:db8::1") in nets
    assert ipaddress.ip_address("2001:db9::1") not in nets
    assert "10.0.0.1" not in nets
    assert len(nets) == 4
    assert {str(n) for n in nets} >= {"10.0.0.0/8", "2001:db8::/32"}


def test_sanitize() -> None:
    assert sanitize_path("/api/webhook/supersecretwebhookid") == "/api/webhook/<redacted>"
    assert sanitize_path("/api/hassio_ingress/token/x") == "/api/hassio_ingress/<redacted>"
    assert sanitize_path("/auth/token?code=abc") == "/auth/token"
    assert sanitize_path("/local/" + "a" * 30) == "/local/<redacted>"
    assert len(sanitize_path("/" + "a/" * 300)) <= 256
    assert sanitize_user_agent(None) is None
    assert sanitize_user_agent("a\x00b\nc") == "abc"
    assert len(sanitize_user_agent("x" * 1000) or "") == 256


def test_durations_and_ladder() -> None:
    assert parse_duration("30m") == timedelta(minutes=30)
    assert parse_duration("2W") == timedelta(weeks=2)
    assert parse_duration("permanent") is None
    for bad in ("0h", "1y", "soon"):
        with pytest.raises(SettingsError):
            parse_duration(bad)
    assert parse_escalation("1h, 24h permanent") == [
        timedelta(hours=1),
        timedelta(hours=24),
        None,
    ]
    for bad in ("", "permanent, 1h"):
        with pytest.raises(SettingsError):
            parse_escalation(bad)


def test_overrides() -> None:
    rules = parse_overrides("# comment\n10.0.0.0/8: 20/60\n10.1.0.0/16 off\n\n2001:db8::/32: 3")
    assert [r.threshold for r in rules] == [20, 0, 3]
    assert rules[2].window == timedelta(0)
    settings = protection_settings({"network_overrides": "10.0.0.0/8: 20/60\n10.1.0.0/16 off"})
    assert settings.rule_for(ipaddress.ip_address("10.1.1.1"))[0] == 0
    assert settings.rule_for(ipaddress.ip_address("10.2.1.1")) == (20, timedelta(minutes=60))
    assert settings.rule_for(ipaddress.ip_address("8.8.8.8")) == (5, timedelta(minutes=15))
    assert ipaddress.ip_address("10.1.0.1") in override_networks(rules)
    for bad in ("nonsense", "10.0.0.0/8: x/y", "10.0.0.0/8: 0/5", "999.0.0.0/8: 3/3"):
        with pytest.raises(SettingsError):
            parse_overrides(bad)
    assert settings.duration_for(1) == timedelta(hours=1)
    assert settings.duration_for(99) is None
    for bad in ({"threshold": 0}, {"window_minutes": 0}):
        with pytest.raises(SettingsError):
            protection_settings(bad)


def test_countries() -> None:
    assert parse_countries("de, at ch") == frozenset({"DE", "AT", "CH"})
    with pytest.raises(SettingsError):
        parse_countries("DEU")
    with pytest.raises(SettingsError):
        country_rules({"country_allow": "DE", "country_deny": "de"})


def test_models_round_trip() -> None:
    now = dt_util.utcnow()
    ban = Ban(parse_network("10.0.0.0/8"), "r", "manual", "me", now, now + timedelta(hours=1), 2)
    again = Ban.from_dict(ban.as_dict())
    assert again == ban and not again.single and not again.permanent
    naive = Ban.from_dict({"ip": "1.2.3.4", "created_at": "2026-01-01T00:00:00"})
    assert naive.created_at.tzinfo is not None
    with pytest.raises(ValueError):
        Ban.from_dict({"ip": "1.2.3.4", "expires_at": "not a date"})
    allow = AllowEntry("host.example", "", None, now, ["1.2.3.4", "junk"])
    assert [str(n) for n in allow.networks()] == ["1.2.3.4/32"]
    assert AllowEntry.from_dict(allow.as_dict()).resolved == ["1.2.3.4", "junk"]
    offense = Offense(3, now)
    assert Offense.from_dict(offense.as_dict()) == offense
    act = Activity(1, now, "ban", "1.2.3.4", detail="d")
    assert Activity.from_dict(act.as_dict()) == act


def test_bansfile(tmp_path: Path) -> None:
    path = tmp_path / "ip_bans.yaml"
    assert bansfile.read_bans(str(path)) == {}
    path.write_text("")
    assert bansfile.read_bans(str(path)) == {}
    path.write_text(
        "1.2.3.4:\n  banned_at: '2026-01-01T00:00:00'\n"
        "5.6.7.8:\n"
        "'::ffff:9.9.9.9':\n  banned_at: '2026-01-01T00:00:00+00:00'\n"
        "junk: {}\n"
    )
    bans = bansfile.read_bans(str(path))
    assert set(bans) == {"1.2.3.4", "5.6.7.8", "9.9.9.9"}
    assert bans["1.2.3.4"].tzinfo is not None
    bansfile.update_bans(str(path), {"10.0.0.1": dt_util.utcnow()}, ["5.6.7.8", "9.9.9.9"])
    text = path.read_text()
    assert "junk" in text and "10.0.0.1" in text and "5.6.7.8" not in text
    bansfile.update_bans(str(path), {}, ["1.2.3.4", "10.0.0.1"])
    path.write_text("- a list\n")
    with pytest.raises(HomeAssistantError):
        bansfile.read_bans(str(path))
    path.write_text("a: [unclosed\n")
    with pytest.raises(HomeAssistantError):
        bansfile.read_bans(str(path))
    path.write_text("1.2.3.4: {}\n")
    bansfile.update_bans(str(path), {}, ["1.2.3.4"])
    assert path.read_text() == ""
