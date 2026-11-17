"""Brand images Home Assistant serves from custom_components/ban_guard/brand/."""

from __future__ import annotations

from pathlib import Path

from PIL import Image
import pytest

BRAND = Path(__file__).resolve().parent.parent / "custom_components" / "ban_guard" / "brand"

# Names Home Assistant's local brands view accepts (homeassistant/components/brands).
ALLOWED = {
    "icon.png",
    "logo.png",
    "icon@2x.png",
    "logo@2x.png",
    "dark_icon.png",
    "dark_logo.png",
    "dark_icon@2x.png",
    "dark_logo@2x.png",
}


def test_only_recognised_files() -> None:
    files = {p.name for p in BRAND.iterdir()}
    assert files <= ALLOWED
    assert {"icon.png", "icon@2x.png", "logo.png", "logo@2x.png"} <= files


@pytest.mark.parametrize(("name", "side"), [("icon.png", 256), ("icon@2x.png", 512)])
def test_icon(name: str, side: int) -> None:
    with Image.open(BRAND / name) as img:
        assert img.format == "PNG"
        assert img.mode == "RGBA"
        assert img.size == (side, side)
        assert img.getpixel((0, 0))[3] == 0  # transparent background
        # Trimmed: the artwork touches at least one pair of opposite edges.
        left, top, right, bottom = img.getchannel("A").getbbox()
        assert (left, right) == (0, side) or (top, bottom) == (0, side)


@pytest.mark.parametrize(
    ("name", "height"),
    [("logo.png", 256), ("logo@2x.png", 512), ("dark_logo.png", 256), ("dark_logo@2x.png", 512)],
)
def test_logo(name: str, height: int) -> None:
    with Image.open(BRAND / name) as img:
        assert img.format == "PNG"
        assert img.mode == "RGBA"
        width, h = img.size
        assert h == height
        assert width > height  # landscape
        assert img.getpixel((0, 0))[3] == 0
        assert img.getchannel("A").getbbox() == (0, 0, width, height)  # trimmed


async def test_home_assistant_serves_brand(hass, hass_client) -> None:  # type: ignore[no-untyped-def]
    """HA 2026.10+ serves the images from the integration's brand/ folder."""
    pytest.importorskip("homeassistant.components.brands")
    from homeassistant.setup import async_setup_component

    from .conftest import setup_deps

    await setup_deps(hass)
    assert await async_setup_component(hass, "brands", {})
    client = await hass_client()
    for name in ("icon.png", "logo.png", "dark_logo@2x.png"):
        resp = await client.get(f"/api/brands/integration/ban_guard/{name}?placeholder=no")
        assert resp.status == 200, name
        assert await resp.read() == (BRAND / name).read_bytes()
