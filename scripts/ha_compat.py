"""Helpers for .github/workflows/ha-compat.yml (stdlib only).

  python scripts/ha_compat.py latest   -> newest test harness pinned to a final HA release
  python scripts/ha_compat.py beta     -> newest HA pre-release newer than the newest final
  python scripts/ha_compat.py bump X   -> pin requirements_test.txt to harness version X

Results are written as key=value lines to $GITHUB_OUTPUT (and stdout).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import sys
import urllib.request

PYPI = "https://pypi.org/pypi/{}/json"
HARNESS = "pytest-homeassistant-custom-component"
REQUIREMENTS = Path(__file__).resolve().parent.parent / "requirements_test.txt"
_PIN = re.compile(rf"^{re.escape(HARNESS)}==(\S+)", re.MULTILINE)


def _json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.load(resp)


def _key(version: str) -> tuple[int, ...]:
    return tuple(int(x) for x in re.findall(r"\d+", version))


def _is_final(version: str) -> bool:
    return re.fullmatch(r"\d+\.\d+\.\d+", version) is not None


def output(**values: str) -> None:
    lines = [f"{k}={v}" for k, v in values.items()]
    print("\n".join(lines))
    if path := os.environ.get("GITHUB_OUTPUT"):
        with open(path, "a", encoding="utf8") as fh:
            fh.write("\n".join(lines) + "\n")


def current_pin() -> str:
    match = _PIN.search(REQUIREMENTS.read_text("utf8"))
    if not match:
        raise SystemExit(f"No {HARNESS} pin in {REQUIREMENTS}")
    return match.group(1)


def ha_pin(harness_version: str) -> str | None:
    info = _json(f"https://pypi.org/pypi/{HARNESS}/{harness_version}/json")["info"]
    for req in info.get("requires_dist") or []:
        match = re.match(r"homeassistant\s*\(?==\s*([^\s);]+)", req)
        if match:
            return match.group(1)
    return None


def latest() -> None:
    releases = _json(PYPI.format(HARNESS))["releases"]
    for version in sorted(releases, key=_key, reverse=True)[:30]:
        ha = ha_pin(version)
        if ha and _is_final(ha):
            pin = current_pin()
            output(
                harness=version,
                ha_version=ha,
                current=pin,
                newer=str(_key(version) > _key(pin)).lower(),
            )
            return
    raise SystemExit("No harness release pinned to a final Home Assistant version found")


def beta() -> None:
    releases = _json(PYPI.format("homeassistant"))["releases"]
    versions = sorted(releases, key=_key)
    final = [v for v in versions if _is_final(v)][-1]
    pre = [v for v in versions if not _is_final(v) and _key(v)[:2] > _key(final)[:2]]
    output(beta=pre[-1] if pre else "", stable=final)


def bump(version: str) -> None:
    text = REQUIREMENTS.read_text("utf8")
    REQUIREMENTS.write_text(_PIN.sub(f"{HARNESS}=={version}", text), "utf8")


def main(argv: list[str]) -> None:
    match argv:
        case ["latest"]:
            latest()
        case ["beta"]:
            beta()
        case ["bump", version]:
            bump(version)
        case _:
            raise SystemExit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
