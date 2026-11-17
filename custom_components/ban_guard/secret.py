"""Encrypt credentials stored in the config entry.

The key lives in its own `.storage/ban_guard.secret` file, separate from the
config entry, so that config entry dumps (diagnostics, shared snippets) never
contain usable credentials. Anyone with full access to the `.storage`
directory can still decrypt them; that is a property of every local secret
store without a hardware key.
"""

from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import STORAGE_KEY_SECRET, STORAGE_VERSION


class SecretBox:
    """Fernet encryption with a key kept in `.storage`."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Init."""
        self._store: Store[dict[str, str]] = Store(
            hass, STORAGE_VERSION, STORAGE_KEY_SECRET, private=True
        )
        self._fernet: Fernet | None = None

    async def _get(self) -> Fernet:
        if self._fernet is None:
            data = await self._store.async_load()
            if not data or "key" not in data:
                data = {"key": Fernet.generate_key().decode()}
                await self._store.async_save(data)
            self._fernet = Fernet(data["key"].encode())
        return self._fernet

    async def async_encrypt(self, plaintext: str) -> str:
        """Encrypt to a URL-safe token."""
        return (await self._get()).encrypt(plaintext.encode()).decode()

    async def async_decrypt(self, token: str) -> str | None:
        """Decrypt, returning None when the token or key is invalid."""
        try:
            return (await self._get()).decrypt(token.encode()).decode()
        except (InvalidToken, ValueError):
            return None

    async def async_remove(self) -> None:
        """Delete the key."""
        await self._store.async_remove()
