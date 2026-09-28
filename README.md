# ServiceNow Job Crawler

Finds legitimate ServiceNow jobs faster than Indeed or other ATS aggregators.
Crawls career boards directly + free job APIs, matches against a tuned
ServiceNow filter (US + Canada), dedupes, and pings Discord on new matches.

Zero paid APIs. Everything here is free.

## How it runs

Two halves, because Workday blocks datacenter IPs:

| What | Where | Boards |
|---|---|---|
| `run.py` | GitHub Actions, twice daily | Greenhouse, Lever, Ashby (2,251 boards) + free APIs |
| `workday_sweep.py` | Local machine (cron), twice daily | 22 priority Workday boards (consultancies + enterprises) |

Both post new matches to the same Discord webhook. Dedupe is per-half
(`jobs.db` for Actions, `workday_seen.json` for the local sweep).

## Quick start

```bash
pip install -r requirements.txt
cp .env.example .env   # fill in DISCORD_WEBHOOK_URL + free API keys
python run.py --dry-run --limit 5   # test without touching jobs.db
python run.py                        # full run
```

Local Workday sweep (needs a residential IP — Workday 400s datacenter IPs):

```bash
python workday_sweep.py
```

## Project layout

```
crawler/
  boards.py    Greenhouse / Lever / Ashby crawlers (cloud-safe)
  workday.py   Workday crawler — LOCAL ONLY, see module docstring
  freeapis.py  Jobicy (keyless), Adzuna, USAJobs
  match.py     ServiceNow matcher: title → location → gov check → keywords
  store.py     SQLite dedupe + run history
  notify.py    Discord webhook alerts
run.py             Actions entry point (skips Workday by design)
workday_sweep.py   Local Workday sweep (priority boards)
companies.json     2,251 ATS boards (greenhouse/lever/ashby)
workday_boards.json  203 Workday boards (reference; sweep uses 22 priority)
tests/test_match.py  matcher regression tests
```

## The matcher

`crawler/match.py` — US + Canada only, no US government/federal/clearance
roles. Pipeline: title pre-filter → location region check → government check
(US-only; Canadian government passes) → keyword check with word boundaries
(ServiceNow must appear 2+ times, not a passing mention). 19+ regression
tests pin the behavior in `tests/test_match.py`.

To allow/block a location or employer type, edit the CAPITALIZED lists at
the top of `match.py` — no logic changes needed.

## Adding a board

1. Add `{"company": "...", "platform": "greenhouse|lever|ashby", "board": "..."}`
   to `companies.json` (or `"platform": "workday"` to `workday_boards.json`).
2. Test: `python run.py --dry-run --limit N` won't help for a single board —
   instead crawl it directly and check the matcher:

```python
from crawler.boards import crawl_company
from crawler.match import job_matches
jobs, err = crawl_company({"company": "Acme", "platform": "lever", "board": "acme"})
print(err or f"{len(jobs)} jobs")
for j in jobs:
    ok, reason = job_matches(j)
    if ok: print("MATCH:", j["title"], j["location"])
```

## Secrets

`.env` is gitignored. GitHub Actions uses repo secrets:
`DISCORD_WEBHOOK_URL` (required), `ADZUNA_APP_ID` / `ADZUNA_APP_KEY`,
`USAJOBS_API_KEY` / `USAJOBS_EMAIL` (optional — free APIs).
