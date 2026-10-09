#!/usr/bin/env python3
"""Publish the built recap into the personal site repo (theycallmegtab.dev).

The site is an Astro project; anything under its public/ folder is served as-is, so the
recap lands at https://theycallmegtab.dev/projects/nba-last-night/ with no Astro changes
beyond the project card. Vercel redeploys the site when the commit reaches main.

Usage:
    python scripts/publish_site.py --site ../theycallmegtab.dev                  # copy only
    python scripts/publish_site.py --site ../theycallmegtab.dev --commit --push  # copy, commit, push

Standard library + git.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEST = Path("public/projects/nba-last-night")
TRAILERS = ("\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>")


def git(site: Path, *args: str, capture: bool = False) -> str:
    res = subprocess.run(["git", "-C", str(site), *args], check=True, text=True,
                         stdout=subprocess.PIPE if capture else None)
    return res.stdout or ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", default=str(ROOT.parent / "theycallmegtab.dev"), help="path to the site repo clone")
    ap.add_argument("--branch", default="main", help="site branch to publish to")
    ap.add_argument("--commit", action="store_true", help="commit the change in the site repo")
    ap.add_argument("--push", action="store_true", help="push the commit (implies --commit)")
    ap.add_argument("--author", help='commit author, e.g. "gtabot <gregg.tabot@gmail.com>"')
    ap.add_argument("--session", help="Claude session URL to add as a commit trailer")
    args = ap.parse_args()

    site = Path(args.site).resolve()
    if not (site / "astro.config.mjs").exists() or not (site / "public").is_dir():
        print(f"{site} doesn't look like the theycallmegtab.dev repo (no astro.config.mjs or public/).")
        return 1

    with tempfile.TemporaryDirectory() as tmp:
        build = subprocess.run([sys.executable, str(ROOT / "scripts" / "build.py"), "--out", tmp])
        if build.returncode:
            return build.returncode
        dest = site / DEST
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(tmp, dest)

    latest = max(ROOT.glob("data/*.json"))
    label = json.loads(latest.read_text(encoding="utf-8"))["nightLabel"]
    print(f"Copied the recap into {dest}")

    if not (args.commit or args.push):
        return 0

    git(site, "add", "-A", str(DEST))
    if not git(site, "diff", "--cached", "--name-only", capture=True).strip():
        print("Nothing changed on the site; no commit made.")
        return 0
    message = f"nba-last-night: {label}" + TRAILERS
    if args.session:
        message += f"\nClaude-Session: {args.session}"
    cmd = ["commit", "-q", "-m", message]
    if args.author:
        cmd.insert(1, f"--author={args.author}")
    git(site, *cmd)
    print("Committed:", git(site, "log", "-1", "--format=%h %s", capture=True).strip())

    if args.push:
        git(site, "fetch", "-q", "origin", args.branch)
        git(site, "rebase", "-q", f"origin/{args.branch}")
        git(site, "push", "-q", "origin", f"HEAD:{args.branch}")
        print(f"Pushed to {args.branch}; Vercel will redeploy the site.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
