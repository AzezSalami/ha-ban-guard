"""Smoke test: the integration loads with http and hooks in."""

from custom_components.ban_guard.manager import BanGuardManager


async def test_loads(manager: BanGuardManager) -> None:
    assert manager.hook_status == "active"
