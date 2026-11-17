"""Sidebar panel registration."""

from __future__ import annotations

import json
from pathlib import Path

from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant, callback

from .const import (
    DOMAIN,
    NAME,
    PANEL_COMPONENT,
    PANEL_FILENAME,
    PANEL_ICON,
    PANEL_STATIC_URL,
    PANEL_URL_PATH,
)

FRONTEND_DIR = Path(__file__).parent / "frontend"
_DATA_STATIC = f"{DOMAIN}_static_registered"


def _version() -> str:
    manifest = json.loads((Path(__file__).parent / "manifest.json").read_text("utf-8"))
    return str(manifest.get("version", "0"))


async def async_register_panel(hass: HomeAssistant) -> None:
    """Serve the bundle and add the admin-only sidebar panel."""
    if not hass.data.get(_DATA_STATIC):
        await hass.http.async_register_static_paths(
            [
                StaticPathConfig(
                    f"{PANEL_STATIC_URL}/{PANEL_FILENAME}",
                    str(FRONTEND_DIR / PANEL_FILENAME),
                    cache_headers=False,
                )
            ]
        )
        hass.data[_DATA_STATIC] = True
    if PANEL_URL_PATH in hass.data.get(frontend.DATA_PANELS, {}):
        return
    version = await hass.async_add_executor_job(_version)
    await panel_custom.async_register_panel(
        hass,
        frontend_url_path=PANEL_URL_PATH,
        webcomponent_name=PANEL_COMPONENT,
        sidebar_title=NAME,
        sidebar_icon=PANEL_ICON,
        module_url=f"{PANEL_STATIC_URL}/{PANEL_FILENAME}?v={version}",
        require_admin=True,
        config={},
    )


@callback
def async_unregister_panel(hass: HomeAssistant) -> None:
    """Remove the sidebar panel."""
    if PANEL_URL_PATH in hass.data.get(frontend.DATA_PANELS, {}):
        frontend.async_remove_panel(hass, PANEL_URL_PATH)
