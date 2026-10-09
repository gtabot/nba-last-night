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


def page(template: str, data: dict, archive: list[dict]) -> str:
    return template.replace(PLACEHOLDER, embed({**data, "archive": archive}), 1)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "dist"))
    ap.add_argument("--keep", type=int, default=30, help="earlier nights to list in the footer")
    out = Path(ap.parse_args().out)
    keep = ap.parse_args().keep

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

    def archive_for(current: str, prefix: str) -> list[dict]:
        return [{"href": f"{prefix}{d['night']}/", "label": d["nightLabel"]}
                for d in nights if d["night"] != current][:keep]

    latest = nights[0]
    (out / "index.html").write_text(page(template, latest, archive_for(latest["night"], "")), encoding="utf-8")
    for d in nights:
        folder = out / d["night"]
        folder.mkdir()
        (folder / "index.html").write_text(page(template, d, archive_for(d["night"], "../")), encoding="utf-8")

    print(f"Built {len(nights)} night(s) into {out} (latest: {latest['night']}, {len(latest['games'])} games)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
