---
name: nightly-recap
description: Gather last night's NBA games from official NBA sources, write data/YYYY-MM-DD.json for the Last Night in the NBA site, validate it, and commit it. Use for the daily morning run or to (re)build any night.
---

# Nightly recap

Produces one data file, `data/YYYY-MM-DD.json`, in the format in `docs/data-format.md`. The page itself never changes during a nightly run — only data.

## 0. Which night

Default: yesterday's date in America/Los_Angeles. If the user names a date, use that. If no NBA games were played that date, stop and report "No games last night" — don't create a file.

## 1. Sources (strict)

Game data comes ONLY from NBA-owned sources:
- `www.nba.com` pages
- official game book PDFs on `statsdmz.nba.com`
- the NBA's own YouTube channel (@NBA)

The one exception: Basketball Reference **player ids**, used only to build links. Never use ESPN, CBS, Yahoo, surprisesports, Bleacher Report or fan sites for anything, even to fill gaps. If the NBA hasn't published something yet, leave it null or mark the game partial (step 4). Never invent or estimate a number.

Tools: WebSearch and WebFetch for finding things. A cloud session's `statsdmz.nba.com` (game books) and `cdn.nba.com` often fail (timeouts, 403), and WebFetch only summarizes pages, so it misses data that nba.com loads client-side.

**Primary data source: the nba.com box-score page, fetched with `curl` from Bash.** `curl -sS -m 40 -A "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36" https://www.nba.com/game/<away>-vs-<home>-<gameId>/box-score` returns HTML with a `<script id="__NEXT_DATA__">` JSON blob. Parse `props.pageProps` with Python (`python3 -I`, save the page to a scratch dir first):
- `game`: `gameEt` (listed tip, already Eastern), `duration` ("0:00" = unpublished, so null), `attendance` (0 = null), `arena`, `homeTeam`/`awayTeam` with `score`, `periods` and `players[].statistics` (full box score), `highlightVideos` (nba.com video permalinks).
- `playByPlay.actions`: every play with `scoreAway`/`scoreHome`. Start of Q1 (`startET`) is in the "Start of 1st Period (h:mm AM/PM ...)" action. Build `flow` only from made shots and made free throws (description has `(N PTS)`, not `MISS`), because non-scoring actions such as instant replays carry stale scores. Sort them by total score, then actionNumber, and only then diff. Clock is `PT11M41.00S`, so use whole seconds.
- Do this yourself rather than via subagents: it is a few `curl` calls and one script. The game book is only a fallback and the source of "Game Duration" when it is reachable.
- Basketball Reference rosters work with `curl` too (single-quoted hrefs: `<a href='/players/t/thomame01.html'>`), as does the YouTube oEmbed check.
- Do not conclude "unreachable" from WebFetch or from `statsdmz`/`cdn.nba.com` alone. Try the curl page above first. Running the check through the proxy does not help; the session already uses it.

## 2. Per game (use the curl method above; subagents only if the volume needs it, and tell them about curl)

1. **Game list, ids, listed tip times:** WebFetch `https://www.nba.com/games?date=YYYY-MM-DD` (and `https://www.nba.com/schedule` if tip times aren't shown).
2. **Official game book:** `https://statsdmz.nba.com/pdfs/YYYYMMDD/YYYYMMDD_AWYHOM_book.pdf` with nba.com codes (e.g. `20261008_PHIBKN_book.pdf`). WebFetch summarizes, so ask for ONE section per call and ask for exact rows:
   - every player's line: MIN, FGM-A, 3PM-A, FTM-A, OR, DR, TOT, A, PF, ST, TO, BS, PTS
   - inactive / DNP list with reasons
   - line score, Q1 "Start of Period" time, last "End of Period" time, "Game Duration", attendance, overtime
   - every scoring play with the running score, one or two quarters per call

   Book times are in the **arena's local time zone** — convert to Eastern. The book's play-by-play prints the **home** score first — convert to away-home. If the book stops before the end of the game, it is partial: use only what it covers.
3. **Final score of a partial game:** the nba.com recap video title, "Game Recap: <Winner> <pts>, <Loser> <pts>" (WebSearch with `allowed_domains: ["nba.com"]`).
4. **Player ids**
   - nba.com: WebSearch `"<name> nba.com player"` and read the number from `https://www.nba.com/player/<id>/<slug>`. Get at least the top 5 per team by game score (the page shows 4); null for the rest.
   - Basketball Reference: WebFetch `https://www.basketball-reference.com/teams/<CODE>/<season end year>.html` (codes match nba.com except BKN→BRK, PHX→PHO, CHA→CHO; 2026-27 → 2027) and ask for every roster player as `Full Name | id` from the `/players/x/<id>.html` links. Match names ignoring accents, punctuation and Jr./III. For anyone missing, WebSearch `"<name> basketball-reference"` with `allowed_domains: ["basketball-reference.com"]`. Null if not found.
5. **Videos** (at most 5 per game)
   - The nba.com game recap video URL (`src: "nba"`, `kind: "recap"`) — always include when it exists.
   - YouTube videos about this game posted by the NBA (full-game highlights, player highlights). Find candidates with WebSearch `allowed_domains: ["youtube.com"]`. **Verify each** with WebFetch of `https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v=<ID>&format=json` and keep it only if `author_name` is exactly `"NBA"`. Try once for view counts; null if rate-limited.
   - Prefer YouTube over NBA.com: YouTube videos can play inline on the page. Add nba.com/watch player highlight pages for this game (`src: "nba"`) only when there are slots left after the NBA's YouTube videos.

## 3. Writing

- `headline` (≤ 60 chars), `story` (3–4 sentences) and the night `summary` (2–3 sentences) are AI-written, in your own words, from the official data only. Never copy sentences from any source.
- Check every claim against the box score and flow: runs, biggest leads, ties, when a team went ahead for good, who led in what. Compute them; don't eyeball.
- Absences come from the book's inactive/DNP list, worded as "did not play" or "were without" — never guess at injuries the book doesn't state.
- Plain, direct sentences. No hype words, no em-dash asides.

## 4. Partial games

If a game book doesn't cover the whole game yet:
- set `flowThrough` (last period covered), `throughET`, and a one-sentence `partial` note
- `box` and `flow` cover only those periods
- `durationMin` is null
- the final score and the missing quarter totals come from the nba.com recap title (by subtraction)

## 5. Validate, build, commit

```bash
python scripts/validate.py data/YYYY-MM-DD.json
python -m unittest discover -s tests
python scripts/build.py          # local check that the page builds
```

Fix or null anything that fails — never weaken the validator to make data pass. Then commit only the data file:

```bash
git add data/YYYY-MM-DD.json
git commit -m "Recap for <Weekday, Month D, YYYY>: <N> games"
git push origin main
```

Pushing to `main` triggers the GitHub Actions workflow, which validates, builds and deploys to GitHub Pages.

## 6. Report

End with 2–3 lines: games covered, any partial games or nulls, and any game without NBA YouTube videos.
