"""Shared fixtures for Ban Guard tests."""

from __future__ import annotations

from collections.abc import AsyncGenerator, Generator
import tempfile
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_mock_service

from custom_components.ban_guard.const import DOMAIN
from custom_components.ban_guard.manager import BanGuardManager
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

pytest_plugins = ["pytest_homeassistant_custom_component"]


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Enable custom integrations in every test."""


@pytest.fixture(autouse=True)
def _mock_panel() -> Generator[dict[str, AsyncMock]]:
    """The real frontend is not installed in the test env; stub panel registration."""
    with (
        patch("custom_components.ban_guard.async_register_panel", AsyncMock()) as register,
        patch("custom_components.ban_guard.async_unregister_panel") as unregister,
    ):
        yield {"register": register, "unregister": unregister}


@pytest.fixture(autouse=True)
def _mock_adapters() -> Generator[None]:
    """Give the HA host a fixed LAN address."""
    adapters = [
        {
            "name": "eth0",
            "enabled": True,
            "auto": True,
            "default": True,
            "ipv4": [{"address": "192.168.1.10", "network_prefix": 24}],
            "ipv6": [{"address": "fe80::10", "network_prefix": 64, "flowinfo": 0, "scope_id": 2}],
        }
    ]
    with patch(
        "homeassistant.components.network.async_get_adapters",
        AsyncMock(return_value=adapters),
    ):
        yield


HTTP_CONFIG: dict[str, Any] = {
    "ip_ban_enabled": True,
    "login_attempts_threshold": 5,
    "use_x_forwarded_for": True,
    "trusted_proxies": ["127.0.0.1", "::1"],
}


async def setup_deps(hass: HomeAssistant, http: dict[str, Any] | None = None) -> None:
    """Set up http and mark the frontend dependencies as loaded."""
    hass.config.config_dir = tempfile.mkdtemp(prefix="ban_guard_test_")
    hass.config.components.update({"frontend", "panel_custom", "network"})
    # HA reverts an unconfirmed pending HTTP config after a timeout by restarting;
    # time-travel tests would trigger that, so provide a no-op restart action.
    async_mock_service(hass, "homeassistant", "restart")
    assert await async_setup_component(hass, "http", {"http": http or HTTP_CONFIG})


@pytest.fixture
async def http(hass: HomeAssistant) -> None:
    """Set up http with IP banning enabled."""
    await setup_deps(hass)


@pytest.fixture
def options() -> dict[str, Any]:
    """Config entry options (override per test)."""
    return {}


@pytest.fixture
async def entry(
    hass: HomeAssistant, http: None, options: dict[str, Any]
) -> AsyncGenerator[MockConfigEntry]:
    """A loaded Ban Guard config entry."""
    config_entry = MockConfigEntry(domain=DOMAIN, title="Ban Guard", data={}, options=options)
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    yield config_entry


@pytest.fixture
def manager(entry: MockConfigEntry) -> BanGuardManager:
    """The manager of the loaded entry."""
    return entry.runtime_data  # type: ignore[no-any-return]
