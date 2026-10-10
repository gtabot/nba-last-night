#!/usr/bin/env python3
"""Build the static site from site/template.html and the nightly data files.

Output (default dist/):
    dist/index.html               the latest night
    dist/YYYY-MM-DD/index.html    every night, including the latest

Every data file is validated first; the build stops if any file fails.
Usage: python scripts/build.py [--out dist]
Standard library only.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate import DATA_DIR, ROOT, validate  # noqa: E402

TEMPLATE = ROOT / "site" / "template.html"
PLACEHOLDER = "__DATA__"


def embed(data: dict) -> str:
    """JSON that is safe inside <script type="application/json">."""
    return json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def page(template: str, data: dict, nav: dict) -> str:
    return template.replace(PLACEHOLDER, embed({**data, **nav}), 1)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "dist"))
    out = Path(ap.parse_args().out)

    template = TEMPLATE.read_text(encoding="utf-8")
    if template.count(PLACEHOLDER) != 1:
        print(f"{TEMPLATE} must contain {PLACEHOLDER} exactly once")
        return 1

    nights = []
    problems = []
    for f in sorted(DATA_DIR.glob("*.json")):
        data = json.loads(f.read_text(encoding="utf-8"))
        problems += validate(data, f.name)
        if f.stem != data.get("night"):
            problems.append(f"{f.name}: file name must match night ({data.get('night')})")
        nights.append(data)
    if problems:
        print("Build stopped; fix these data problems first:")
        print("\n".join(problems))
        return 1
    if not nights:
        print("No data files in data/.")
        return 1

    nights.sort(key=lambda d: d["night"], reverse=True)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    def nav_for(i: int, prefix: str) -> dict:
        """The latest night's page, this night's own page, plus the night before (older) and the night after (newer), if built."""
        link = lambda d: {"href": f"{prefix}{d['night']}/", "label": d["nightLabel"]}
        return {"homeHref": prefix or "./",
                "nightHref": f"{prefix}{nights[i]['night']}/",
                "prevNight": link(nights[i + 1]) if i + 1 < len(nights) else None,
                "nextNight": link(nights[i - 1]) if i > 0 else None}

    latest = nights[0]
    (out / "index.html").write_text(page(template, latest, nav_for(0, "")), encoding="utf-8")
    for i, d in enumerate(nights):
        folder = out / d["night"]
        folder.mkdir()
        (folder / "index.html").write_text(page(template, d, nav_for(i, "../")), encoding="utf-8")

    print(f"Built {len(nights)} night(s) into {out} (latest: {latest['night']}, {len(latest['games'])} games)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
