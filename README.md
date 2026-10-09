# Last Night in the NBA

Live at **https://theycallmegtab.dev/projects/nba-last-night/**, as part of [theycallmegtab.dev](https://github.com/gtabot/theycallmegtab.dev).

A single scrolling page that recaps the previous night's NBA games: an AI-written summary of the night, a draggable score ticker, a tip-off board, and a collapsible section for each tip-off window. Each game has its line score, a recap, a margin-by-game-clock chart, official NBA videos, and its top performers by game score.

All game data comes from official NBA sources (the NBA's game books, NBA.com and the NBA's YouTube channel). Headlines, recaps and the night summary are AI-generated from that data and labeled as such. Not affiliated with the NBA.

## How it works

```
morning research (Claude scheduled task, .claude/skills/nightly-recap)
   │ writes + validates
   ▼
data/YYYY-MM-DD.json ──commit──► this repo ──► GitHub Actions: validate, test, build (checks only)
   │
   │ scripts/publish_site.py
   ▼
theycallmegtab.dev repo: public/projects/nba-last-night/ ──commit──► Vercel redeploys the site
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

Have Claude run the `nightly-recap` skill (the daily scheduled task does this), or write `data/YYYY-MM-DD.json` by hand following the format doc. Commit it, then publish (below). If the data fails validation, the build stops and nothing is published.

## Publishing to theycallmegtab.dev

The site repo serves anything under `public/` as-is, so publishing is a copy plus a commit:

```bash
# with both repos cloned side by side
python scripts/publish_site.py --site ../theycallmegtab.dev --commit --push
```

This builds the page, replaces `public/projects/nba-last-night/` in the site repo, commits (`nba-last-night: <night>`) and pushes to the site's `main`. Vercel deploys the site on that push. Run it after changing the template too, not just after new data.

No GitHub token or secret is involved: the daily scheduled task has access to both repos and runs this step itself.
