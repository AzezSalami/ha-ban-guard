"""Optional Nginx Proxy Manager (NPM) access list sync.

Ban Guard owns one dedicated NPM access list. On every sync its client rules
are replaced with `deny <ban>` for each active ban followed by `allow all`.
Basic-auth items on that list are kept. Outbound calls go only to the NPM URL
the user configured.
"""

from __future__ import annotations

from collections.abc import Iterable
import logging
from typing import Any

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger(__name__)
_TIMEOUT = aiohttp.ClientTimeout(total=20)
NPM_ADDON_MARKERS = ("nginxproxymanager", "nginx_proxy_manager", "nginx-proxy-manager")


class NPMError(Exception):
    """NPM API call failed. `key` is a translation key."""

    def __init__(self, key: str, detail: str = "") -> None:
        """Init."""
        super().__init__(detail or key)
        self.key = key


class NPMClient:
    """Minimal NPM REST client."""

    def __init__(
        self, hass: HomeAssistant, url: str, username: str, password: str, verify_ssl: bool
    ) -> None:
        """Init."""
        self._session = async_get_clientsession(hass, verify_ssl=verify_ssl)
        self._url = url.rstrip("/")
        self._username = username
        self._password = password
        self._token: str | None = None

    async def _request(self, method: str, path: str, json: Any = None, auth: bool = True) -> Any:
        headers = {"accept": "application/json"}
        if auth:
            if self._token is None:
                await self.async_login()
            headers["authorization"] = f"Bearer {self._token}"
        try:
            async with self._session.request(
                method, f"{self._url}{path}", json=json, headers=headers, timeout=_TIMEOUT
            ) as resp:
                if resp.status in (401, 403):
                    raise NPMError("invalid_auth")
                if resp.status == 404:
                    raise NPMError("not_found")
                if resp.status >= 400:
                    raise NPMError("cannot_connect", f"HTTP {resp.status}")
                return await resp.json(content_type=None)
        except aiohttp.ClientError as err:
            raise NPMError("cannot_connect", str(err)) from err
        except TimeoutError as err:
            raise NPMError("cannot_connect", "timeout") from err

    async def async_login(self) -> None:
        """Obtain a token."""
        data = await self._request(
            "POST",
            "/api/tokens",
            {"identity": self._username, "secret": self._password},
            auth=False,
        )
        token = data.get("token") if isinstance(data, dict) else None
        if not token:
            raise NPMError("invalid_auth")
        self._token = str(token)

    async def async_access_lists(self) -> list[dict[str, Any]]:
        """List access lists (id and name)."""
        data = await self._request("GET", "/api/nginx/access-lists")
        if not isinstance(data, list):
            raise NPMError("cannot_connect", "unexpected response")
        return [{"id": int(i["id"]), "name": str(i.get("name", ""))} for i in data]

    async def async_sync(self, list_id: int, denied: Iterable[str]) -> int:
        """Replace the access list's client rules. Returns the number of denies."""
        current = await self._request(
            "GET", f"/api/nginx/access-lists/{list_id}?expand=items,clients"
        )
        if not isinstance(current, dict):
            raise NPMError("cannot_connect", "unexpected response")
        clients = [{"address": addr, "directive": "deny"} for addr in sorted(set(denied))]
        clients.append({"address": "all", "directive": "allow"})
        items = [
            {"username": item.get("username", ""), "password": ""}
            for item in current.get("items") or []
        ]
        body = {
            "name": current.get("name") or "Ban Guard",
            "satisfy_any": bool(current.get("satisfy_any", True)),
            "pass_auth": bool(current.get("pass_auth", False)),
            "items": items,
            "clients": clients,
        }
        await self._request("PUT", f"/api/nginx/access-lists/{list_id}", body)
        return len(clients) - 1


async def async_detect_addon(hass: HomeAssistant) -> dict[str, Any] | None:
    """Find an installed NPM add-on through the Supervisor (no add-on options read)."""
    try:
        from homeassistant.components import hassio  # noqa: PLC0415
        from homeassistant.helpers.hassio import is_hassio  # noqa: PLC0415

        if not is_hassio(hass):
            return None
        addons: list[dict[str, Any]]
        if hasattr(hassio, "get_addons_list"):  # HA 2026.3+
            addons = list(hassio.get_addons_list(hass))
        else:  # older releases: {slug: info}
            addons = [
                {"slug": slug, **(info or {})}
                for slug, info in (hassio.get_addons_info(hass) or {}).items()
            ]
    except Exception:
        _LOGGER.debug("Supervisor add-on list unavailable", exc_info=True)
        return None
    for addon in addons or []:
        slug = str(addon.get("slug", ""))
        name = str(addon.get("name", ""))
        haystack = f"{slug} {name}".lower().replace(" ", "")
        if any(marker in haystack for marker in NPM_ADDON_MARKERS):
            return {
                "slug": slug,
                "name": name,
                "state": addon.get("state"),
                "suggested_url": f"http://{slug.replace('_', '-')}:81",
            }
    return None
