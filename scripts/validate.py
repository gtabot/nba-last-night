#!/usr/bin/env python3
"""Validate nightly recap data files against the format in docs/data-format.md.

Usage:
    python scripts/validate.py                 # every file in data/
    python scripts/validate.py data/2026-10-08.json [...]

Exits non-zero if any file has problems, printing one line per problem.
Standard library only.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"

BOX_COLS = ["name", "pid", "bbref", "min", "fgm", "fga", "tpm", "tpa", "ftm", "fta",
            "orb", "drb", "reb", "ast", "pf", "stl", "tov", "blk", "pts"]
PHASES = {"Preseason", "Regular Season", "NBA Cup", "Play-In", "Playoffs"}
VIDEO_KINDS = {"recap", "highlights", "player", "other"}
HHMM = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
CLOCK = re.compile(r"^\d{2}:[0-5]\d$")
MIN = re.compile(r"^\d{1,2}:[0-5]\d$")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
BBREF = re.compile(r"^[a-z.'-]{1,5}[a-z]{1,2}\d{2}$")
YT_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")


def period_end(p: int) -> int:
    """Elapsed game seconds at the end of period p (1-based); OT periods are 5 minutes."""
    return p * 720 if p <= 4 else 2880 + (p - 4) * 300


def period_len(p: int) -> int:
    return 720 if p <= 4 else 300


def check_game(g: dict, phase: str, err) -> None:
    gid = g.get("id", "?")
    e = lambda msg: err(f"game {gid}: {msg}")

    for key in ("id", "schedET", "startET", "durationMin", "ot", "attendance", "venue", "away", "home",
                "headline", "story", "box", "flow", "videos", "boxUrl", "bookUrl", "sources"):
        if key not in g:
            e(f"missing field '{key}'")
    if not re.fullmatch(r"\d{10}", str(g.get("id", ""))):
        e("id must be the 10-digit nba.com game id")
    if not HHMM.match(str(g.get("schedET", ""))):
        e("schedET must be HH:MM (24h, Eastern)")
    if g.get("startET") is not None and not HHMM.match(str(g["startET"])):
        e("startET must be HH:MM or null")
    if g.get("durationMin") is not None and not (isinstance(g["durationMin"], int) and 60 <= g["durationMin"] <= 300):
        e("durationMin must be minutes between 60 and 300, or null")
    ot = g.get("ot", 0)
    if not isinstance(ot, int) or ot < 0:
        e("ot must be a non-negative integer")
        ot = 0
    periods = 4 + ot
    if len(g.get("headline", "")) > 60:
        e("headline is longer than 60 characters")
    if not g.get("story"):
        e("story is empty")

    thru = g.get("flowThrough", periods)
    partial = "flowThrough" in g
    if partial:
        if not (isinstance(thru, int) and 1 <= thru < periods):
            e("flowThrough must be a period number before the last one")
            thru = periods
        if not g.get("partial"):
            e("partial games need a 'partial' sentence")
        if g.get("durationMin") is not None:
            e("partial games must have durationMin null")

    # teams and line score
    teams = {}
    for side in ("away", "home"):
        t = g.get(side) or {}
        for key in ("abbr", "city", "nick", "color", "score", "q"):
            if key not in t:
                e(f"{side} missing '{key}'")
        if not re.fullmatch(r"[A-Z]{3}", str(t.get("abbr", ""))):
            e(f"{side}.abbr must be a 3-letter nba.com code")
        if not HEX.match(str(t.get("color", ""))):
            e(f"{side}.color must be a #RRGGBB hex")
        q = t.get("q", [])
        if len(q) != periods:
            e(f"{side}.q must have {periods} periods (4 + ot)")
        elif all(isinstance(v, int) for v in q) and sum(q) != t.get("score"):
            e(f"{side}.q sums to {sum(q)}, not the final score {t.get('score')}")
        teams[side] = t
    if teams.get("away", {}).get("score") == teams.get("home", {}).get("score"):
        e("final scores are tied")
    through = {s: sum((teams[s].get("q") or [0])[:thru]) for s in teams}

    # box score
    box = g.get("box") or {}
    if box.get("cols") != BOX_COLS:
        e(f"box.cols must be exactly {BOX_COLS}")
    else:
        idx = {c: i for i, c in enumerate(BOX_COLS)}
        for side in ("away", "home"):
            rows = box.get(side) or []
            if len(rows) < 5:
                e(f"box.{side} has fewer than 5 players")
            total = 0
            for r in rows:
                if len(r) != len(BOX_COLS):
                    e(f"box.{side} row has {len(r)} values: {r[:1]}")
                    continue
                p = {c: r[i] for c, i in idx.items()}
                who = f"box.{side} {p['name']}"
                if p["pid"] is not None and not isinstance(p["pid"], int):
                    e(f"{who}: pid must be an integer or null")
                if p["bbref"] is not None and not BBREF.match(str(p["bbref"])):
                    e(f"{who}: bbref '{p['bbref']}' doesn't look like a Basketball Reference id")
                if not MIN.match(str(p["min"])):
                    e(f"{who}: min must be MM:SS")
                nums = [p[c] for c in BOX_COLS[4:]]
                if not all(isinstance(v, int) and v >= 0 for v in nums):
                    e(f"{who}: stats must be non-negative integers")
                    continue
                if p["pts"] != 2 * p["fgm"] + p["tpm"] + p["ftm"]:
                    e(f"{who}: pts {p['pts']} != 2*FGM + 3PM + FTM")
                if p["reb"] != p["orb"] + p["drb"]:
                    e(f"{who}: reb != orb + drb")
                if not (p["tpm"] <= p["tpa"] and p["fgm"] <= p["fga"] and p["ftm"] <= p["fta"] and p["tpm"] <= p["fgm"] and p["tpa"] <= p["fga"]):
                    e(f"{who}: shooting numbers are inconsistent")
                total += p["pts"]
            if side in through and total != through[side]:
                e(f"box.{side} points sum to {total}, expected {through[side]}")

    # play-by-play
    flow = g.get("flow")
    if flow is not None:
        prev_t, prev = -1, (0, 0)
        for row in flow:
            if not (isinstance(row, list) and len(row) == 4):
                e(f"flow row malformed: {row}")
                break
            p, clock, a, h = row
            if not (isinstance(p, int) and 1 <= p <= thru) or not CLOCK.match(str(clock)):
                e(f"flow row has a bad period/clock: {row}")
                break
            mm, ss = map(int, clock.split(":"))
            if mm * 60 + ss > period_len(p):
                e(f"flow clock exceeds the period length: {row}")
                break
            t = period_end(p) - (mm * 60 + ss)
            step = (a - prev[0]) + (h - prev[1])
            if t < prev_t or a < prev[0] or h < prev[1] or not (1 <= step <= 3) or (a > prev[0] and h > prev[1]):
                e(f"flow is out of order or jumps by more than one score at {row} (previous {prev})")
                break
            prev_t, prev = t, (a, h)
        else:
            want = (through.get("away"), through.get("home"))
            if flow and prev != want:
                e(f"flow ends at {prev}, expected {want}")

    # videos and links
    for v in g.get("videos") or []:
        if v.get("kind") not in VIDEO_KINDS:
            e(f"video kind must be one of {sorted(VIDEO_KINDS)}")
        if v.get("src") == "yt":
            if not YT_ID.match(str(v.get("id", ""))):
                e(f"YouTube id '{v.get('id')}' is not 11 characters")
        elif v.get("src") == "nba":
            if not str(v.get("url", "")).startswith("https://www.nba.com/"):
                e("nba videos need an https://www.nba.com/ url")
        else:
            e("video src must be 'yt' or 'nba'")
        if not v.get("title"):
            e("video is missing a title")
    if not str(g.get("boxUrl", "")).startswith("https://www.nba.com/game/"):
        e("boxUrl must be an nba.com game box score URL")
    if not str(g.get("bookUrl", "")).startswith("https://statsdmz.nba.com/pdfs/"):
        e("bookUrl must be the official game book PDF")
    for u in g.get("sources") or []:
        if not re.match(r"https://(www\.nba\.com|statsdmz\.nba\.com)/", u):
            e(f"source isn't an NBA-owned URL: {u}")


def validate(data: dict, name: str = "data") -> list[str]:
    problems: list[str] = []
    err = lambda msg: problems.append(f"{name}: {msg}")
    for key in ("night", "nightLabel", "phase", "updated", "summary", "games"):
        if key not in data:
            err(f"missing top-level field '{key}'")
    if not DATE.match(str(data.get("night", ""))):
        err("night must be YYYY-MM-DD")
    if data.get("phase") not in PHASES:
        err(f"phase must be one of {sorted(PHASES)}")
    games = data.get("games") or []
    if not games:
        err("games is empty")
    ids = [g.get("id") for g in games]
    if len(ids) != len(set(ids)):
        err("duplicate game ids")
    for g in games:
        check_game(g, data.get("phase"), err)
    if "</script" in json.dumps(data, ensure_ascii=False).lower():
        err("text contains '</script', which would break the page")
    return problems


def main(argv: list[str]) -> int:
    files = [Path(a) for a in argv] or sorted(DATA_DIR.glob("*.json"))
    if not files:
        print("No data files found.")
        return 1
    bad = 0
    for f in files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            print(f"{f.name}: invalid JSON ({exc})")
            bad += 1
            continue
        if f.stem != data.get("night"):
            print(f"{f.name}: file name must match night ({data.get('night')})")
            bad += 1
        problems = validate(data, f.name)
        for p in problems:
            print(p)
        bad += bool(problems)
        if not problems:
            print(f"{f.name}: ok ({len(data['games'])} games)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
