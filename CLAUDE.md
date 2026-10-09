# Last Night in the NBA

A static, single-page recap of the previous night's NBA games. One HTML template plus one JSON data file per night. GitHub Actions validates, builds and deploys it to GitHub Pages at https://gtabot.github.io/nba-last-night/. The personal site (theycallmegtab.dev, repo `gtabot/theycallmegtab.dev`) only has a project entry that links here; it never hosts the page.

## Layout

- `site/template.html` — the whole page (HTML, CSS, JS, no build tools). Contains `__DATA__` exactly once, inside `<script type="application/json" id="recap-data">`.
- `data/YYYY-MM-DD.json` — one night of games. Format: `docs/data-format.md`.
- `scripts/validate.py` — data rules (sums, play-by-play, ids, NBA-only sources). Standard library only.
- `scripts/build.py` — validates every data file, then writes `dist/index.html` (latest night) and `dist/YYYY-MM-DD/index.html` (each night).
- `tests/` — `python -m unittest discover -s tests`.
- `.claude/skills/nightly-recap/` — the daily data-gathering procedure.
- `.github/workflows/deploy.yml` — validate, test, build, and deploy to GitHub Pages on every push to `main` (checks only on pull requests).

## Rules

- **Daily runs change data only.** Never edit `site/template.html` during a nightly run.
- **NBA-only sources** for all game data (nba.com, statsdmz.nba.com game books, the @NBA YouTube channel). Basketball Reference is used only for player ids in links.
- **Never invent numbers.** Unknown → null, or mark the game partial.
- **AI-written text** (headlines, recaps, night summary) must be checkable against the data in the same file. The page labels it "AI-Generated Recap"; keep that label.
- **Never loosen `validate.py` to make bad data pass.** If the format genuinely changes, update `docs/data-format.md`, `validate.py`, the tests and the template together.

## Design decisions (keep unless asked)

- Time sections by listed tip, grouped into 30-minute windows; all collapsed on load; header band animates once its top passes mid-viewport.
- Score-card selectors in a horizontal row; selected game below. Order inside a game: score card → recap + margin chart → dark video panel → top performers → box score links → Previous/Next game.
- Top performers: top 4 per team by game score (`TOP_N` in the template), cards two per row. Stat line rule (`statline()` in the template): pts if ≥ 10 (+ "N 3P" if ≥ 7 threes); then reb/ast (≥ 5) and stl/blk (≥ 2), highest first, up to 3 stats; if fewer than 2, fill with the biggest remaining counting stats (pts first). Chips only ever show counting stats (pts, reb, ast, stl, blk, 3P made), never shooting splits; the splits sit on the line underneath.
- Margin chart: team colors, ±20 default y-axis, expands to the nearest 5.
- Tip-off board: listed tip to final buzzer; unpublished lengths drawn as 2:15, same style.
- Links toggle (NBA.com / Basketball Reference); preseason box scores stay on NBA.com.
- Theme toggle (Light / Dark / Auto). Auto follows the device. An inline script in <head> applies the saved theme before first paint.
- Both preferences are remembered in first-party cookies (`nbaTheme`, `nbaLinks`) for a year, scoped to the site's folder so every night's page shares them. Choosing the default (Auto / NBA.com) deletes the cookie.
- Ticker crawls, is draggable both ways with momentum, and resumes on release.
- No ads (NBA.com terms limit commercial use of their stats).

## Local preview

```bash
python scripts/build.py && python -m http.server -d dist 8000
```
