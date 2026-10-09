# Last Night in the NBA

Live at **https://gtabot.github.io/nba-last-night/** · project page on [theycallmegtab.dev](https://theycallmegtab.dev/projects/nba-last-night).

A single scrolling page that recaps the previous night's NBA games: an AI-written summary of the night, a draggable score ticker, a tip-off board, and a collapsible section for each tip-off window. Each game has its line score, a recap, a margin-by-game-clock chart, official NBA videos, and its top performers by game score.

All game data comes from official NBA sources (the NBA's game books, NBA.com and the NBA's YouTube channel). Headlines, recaps and the night summary are AI-generated from that data and labeled as such. Not affiliated with the NBA.

## How it works

```
morning research (Claude scheduled task, .claude/skills/nightly-recap)
        │  writes + validates
        ▼
data/YYYY-MM-DD.json  ──git push──►  GitHub Actions
                                       ├─ validate.py   (data rules)
                                       ├─ unit tests
                                       ├─ build.py      (template + data → dist/)
                                       └─ deploy to GitHub Pages
```

- **`site/template.html`**: the page. Plain HTML/CSS/JS with no dependencies besides Google Fonts. The night's data is embedded where `__DATA__` appears.
- **`data/`**: one JSON file per night, named by date. The format is documented in [`docs/data-format.md`](docs/data-format.md).
- **`scripts/validate.py`**: checks every file, including:
  - quarter scores sum to the final
  - every player's points add up and the team totals match
  - play-by-play runs in order and ends at the final score
  - ids are well formed
  - sources are NBA-owned
- **`scripts/build.py`**: validates, then writes `dist/index.html` (latest night) and `dist/YYYY-MM-DD/` for every night. Earlier nights are linked in the footer.

## Run it locally

Requires Python 3.10+, with no packages to install.

```bash
python scripts/validate.py                 # check all data files
python -m unittest discover -s tests       # run the tests
python scripts/build.py                    # build into dist/
python -m http.server -d dist 8000         # open http://localhost:8000
```

## Adding a night

Have Claude run the `nightly-recap` skill (the daily scheduled task does this), or write `data/YYYY-MM-DD.json` by hand following the format doc. Commit it and push to `main`; the workflow validates, tests, builds and deploys. If the data fails validation, nothing is published.

## One-time setup

GitHub Pages needs the repo to be public (or a paid GitHub plan for private repos). Then, in **Settings → Pages**, set **Source** to **GitHub Actions** and re-run the latest workflow from the **Actions** tab.
