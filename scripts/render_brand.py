"""Trim, square and resize the brand renders into custom_components/ban_guard/brand/.

Render the SVGs in docs/brand/ first (see docs/brand/README.md), then run:

    python scripts/render_brand.py <dir with raw-icon.png, raw-logo-light.png, raw-logo-dark.png>

Needs Pillow (installed with Home Assistant's test requirements).
"""

from __future__ import annotations

from pathlib import Path
import sys

from PIL import Image

OUT = Path(__file__).resolve().parent.parent / "custom_components" / "ban_guard" / "brand"


def _trim(img: Image.Image) -> Image.Image:
    img = img.convert("RGBA")
    bbox = img.getchannel("A").getbbox()
    if bbox is None:
        raise SystemExit("image is fully transparent")
    return img.crop(bbox)


def _square(img: Image.Image) -> Image.Image:
    side = max(img.size)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.paste(img, ((side - img.width) // 2, (side - img.height) // 2))
    return canvas


def _save(img: Image.Image, name: str, size: tuple[int, int]) -> None:
    img.resize(size, Image.Resampling.LANCZOS).save(OUT / name, optimize=True)
    print(f"{name}: {size[0]}x{size[1]}")


def main(raw: Path) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    icon = _square(_trim(Image.open(raw / "raw-icon.png")))
    _save(icon, "icon.png", (256, 256))
    _save(icon, "icon@2x.png", (512, 512))
    for theme, prefix in (("light", ""), ("dark", "dark_")):
        logo = _trim(Image.open(raw / f"raw-logo-{theme}.png"))
        for height, suffix in ((256, ""), (512, "@2x")):
            width = round(logo.width * height / logo.height)
            _save(logo, f"{prefix}logo{suffix}.png", (width, height))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    main(Path(sys.argv[1]))
