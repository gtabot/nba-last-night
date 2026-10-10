# Nightly data format

One file per night: `data/YYYY-MM-DD.json`, named for the date the games were played (US Eastern). The build embeds it into `site/template.html`; the page computes everything else (rankings, stat lines, charts, colors) in the browser.

`scripts/validate.py` enforces every rule below. Run it before committing.

## Top level

| Field | Type | Notes |
|---|---|---|
| `night` | `"YYYY-MM-DD"` | Must match the file name. |
| `nightLabel` | string | `"Thursday, October 8, 2026"` — shown above the title. |
| `phase` | string | One of `Preseason`, `Regular Season`, `NBA Cup`, `Play-In`, `Playoffs`. Shown as the tag next to the title; `Preseason` also turns off Basketball Reference box score links (that site has no preseason pages). |
| `updated` | string | `"Friday, October 9, 2026 · 6:58 AM PT"` — shown in the footer. |
| `summary` | string | 2–3 sentence AI-written overview of the night. Every claim must be backed by the games' data. |
| `games` | array | One object per game, any order (the page orders by `schedET`). |

The build adds `homeHref` (the site root, which always shows the latest night; linked from the title), `nightHref` (this night's own page, linked from the date at the top), `prevNight` and `nextNight` (`{"href", "label"}` or null, the neighboring built nights) itself — don't put them in data files.

## Game

| Field | Type | Notes |
|---|---|---|
| `id` | string | 10-digit nba.com game id, e.g. `"0012600034"`. |
| `schedET` | `"HH:MM"` | Listed (TV) tip time, Eastern, 24-hour. Drives the time sections and the tip-off board. |
| `startET` | `"HH:MM"` or null | Actual start of Q1 from the game book, converted to Eastern. |
| `durationMin` | int or null | "Game Duration" from the game book in minutes. Null when unpublished; the board then assumes 2:15. |
| `ot` | int | Number of overtime periods. |
| `attendance` | int or null | |
| `venue` | string | `"Arena, City"`. |
| `away`, `home` | object | See Team. |
| `headline` | string | ≤ 60 characters, AI-written. |
| `story` | string | 3–4 sentences, AI-written from the official data only. |
| `box` | object | See Box score. |
| `flow` | array or null | See Play-by-play. |
| `videos` | array | See Videos. |
| `boxUrl` | string | `https://www.nba.com/game/<away>-vs-<home>-<id>/box-score` (lowercase abbreviations). |
| `bookUrl` | string | `https://statsdmz.nba.com/pdfs/YYYYMMDD/YYYYMMDD_AWYHOM_book.pdf`. |
| `sources` | array of URLs | NBA-owned URLs only (`www.nba.com`, `statsdmz.nba.com`). |

Only when the official game book doesn't cover the whole game yet:

| Field | Type | Notes |
|---|---|---|
| `flowThrough` | int | Last period the book covers. `box` and `flow` cover only through this period. |
| `throughET` | `"HH:MM"` | Eastern time of the last "End of Period" in the book. |
| `partial` | string | One plain sentence shown under the score card, e.g. what's covered and where the final score came from. |

`durationMin` must be null for partial games.

### Team

```json
{"abbr": "BOS", "city": "Boston", "nick": "Celtics", "color": "#007A33", "score": 124, "q": [32, 39, 28, 25]}
```

- `abbr`: nba.com three-letter code.
- `color`: team primary hex. The page has its own color table (with alternates for clashing pairs) and uses this only for teams missing from it.
- `q`: points per period, one entry per period including each overtime; must sum to `score`.

### Box score

Every player who played, for both teams, as rows in this exact column order:

```json
"cols": ["name","pid","bbref","min","fgm","fga","tpm","tpa","ftm","fta","orb","drb","reb","ast","pf","stl","tov","blk","pts"]
```

- `pid`: nba.com player id (int) or null. Needed for players who might rank in the top four (get the top five per team to be safe).
- `bbref`: Basketball Reference id such as `"garzalu01"`, or null. Used only to build links.
- `min`: `"MM:SS"`.
- Each row must satisfy `pts = 2·fgm + tpm + ftm` and `reb = orb + drb`; each team's rows must sum to its score (or its score through `flowThrough`).

The page ranks players by game score — `PTS + 0.4·FGM − 0.7·FGA − 0.4·(FTA − FTM) + 0.7·ORB + 0.3·DRB + STL + 0.7·AST + 0.7·BLK − 0.4·PF − TOV` — and shows the top four per team.

### Play-by-play

Every scoring play in order, as `[period, "MM:SS" remaining, awayScore, homeScore]`:

```json
[[1, "10:52", 0, 3], [1, "10:33", 2, 3], ...]
```

Periods 5+ are overtime (5:00 each). Each row changes one team's score by 1–3 points; the last row equals the final score (or the score through `flowThrough`). Free throws are separate rows.

### Videos

```json
{"src": "nba", "url": "https://www.nba.com/watch/video/game-recap-celtics-124-cavaliers-113", "title": "Game Recap: Celtics 124, Cavaliers 113", "kind": "recap"}
{"src": "yt", "id": "FiM7fpIctQI", "title": "CELTICS at CAVALIERS | NBA PRESEASON FULL GAME HIGHLIGHTS | October 8, 2026", "kind": "highlights", "views": null}
```

- `kind`: `recap`, `highlights`, `player` or `other`. The page shows YouTube (`yt`) videos first — they're the ones that can play inline — then NBA.com ones; within each group the recap comes first and the rest sort by `views` (nulls last).
- `yt` videos must be uploaded by the NBA's own channel (checked via YouTube oEmbed `author_name == "NBA"`). On the hosted site they play inline; `nba` videos open NBA.com.
