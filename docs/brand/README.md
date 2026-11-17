# Ban Guard brand assets

Original artwork for Ban Guard: a shield with a padlock and a "no entry" badge.
It is licensed with the project (MIT).

| File | Purpose |
| --- | --- |
| `icon.svg` | Square icon source |
| `logo-light.svg` | Icon and wordmark, for light backgrounds |
| `logo-dark.svg` | Icon and wordmark, for dark backgrounds |

The PNGs Home Assistant uses live in
[`custom_components/ban_guard/brand/`](../../custom_components/ban_guard/brand).
From 2026.10, Home Assistant serves them from there for the integrations page
and the "Add integration" dialog. Older versions show the generic placeholder.

| PNG | Size |
| --- | --- |
| `icon.png` / `icon@2x.png` | 256×256 / 512×512, square, trimmed, transparent |
| `logo.png` / `logo@2x.png` | 256 / 512 px tall, trimmed, transparent |
| `dark_logo.png` / `dark_logo@2x.png` | as above, with a light wordmark for dark themes |

`dark_icon.png` is not needed: the icon works on both backgrounds, and Home
Assistant falls back to `icon.png`.

## Regenerating the PNGs

1. Render each SVG at high resolution with a transparent background, for
   example with headless Edge or Chrome:

   ```bash
   msedge --headless=new --disable-gpu --hide-scrollbars --default-background-color=00000000 --window-size=1024,1024 --screenshot=raw-icon.png file:///path/to/docs/brand/icon.svg
   ```

   Use `--window-size=3000,920` for `logo-light.svg` (saved as `raw-logo-light.png`)
   and `logo-dark.svg` (saved as `raw-logo-dark.png`). The wordmark uses Segoe UI
   Semibold.

2. Trim, square and resize into the integration's `brand/` folder:

   ```bash
   python scripts/render_brand.py <folder with the three raw PNGs>
   ```

`tests/test_brand.py` checks the sizes and transparency of the committed PNGs.
