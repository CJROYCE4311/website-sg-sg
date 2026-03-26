# Codex Workflow

## Goal

Run this directory as a local parallel-processing clone that can:
- review weekly screenshots in chunks
- maintain the canonical CSV files
- regenerate the site locally
- avoid commit and deploy side effects by default

## Canonical vs Generated Files

Canonical:
- `data/scores.csv`
- `data/financials.csv`
- `data/handicaps.csv`
- `data/course_info.csv`
- `data/player_aliases.json`

Canonical notes:
- `scores.csv` stores player performance for the round, including `Differential`.
- `handicaps.csv` stores the handicap snapshot for the date, including `Handicap_Index` and `Course_Handicap`.
- `financials.csv` may stand alone when payout screenshots are preserved but later score rows disappear in Squabbit.
- `player_aliases.json` normalizes known name variants before data is validated or written.
- `2025-01-04` is a known event with financial and handicap data but no gross scorecard data.

Generated:
- `website/DataAudit.html`
- `website/index.html`
- `website/MoneyList2025.html`
- `website/MoneyList2026.html`
- `website/PlayerStats.html`
- `website/AverageScore.html`
- `website/HoleIndex.html`
- `website/HandicapAnalysis.html`
- `website/Handicap_Detail.html`
- `website/data/methodology_data.json`
- `website/data/methodology_data.js`
- `website/results_*.html`

Working area:
- `input/screenshots/`
- `input/history/`
- `input/processed/`
- `input/tournament_data.json`

## Weekly Operating Pattern

1. Place new screenshots in `input/screenshots/`.
2. Extract them in batches to avoid model-limit failures:
   - scorecards
   - payouts
   - skins
   - leaderboard / partners
   - best-ball screenshots can serve two purposes at once:
     - payouts belong in `financials.csv`
     - visible handicap indexes can be used for `handicaps.csv`, but only for players who also have score rows for that date
3. Merge those batches into a reviewed `input/tournament_data.json`.
   - Start from `docs/tournament_data.template.json` so the metadata block is always present.
   - Include a `metadata` block per tournament when possible:
     - `full_scorecard_available`
     - `handicap_list_available`
     - `screenshots`
     - `source_notes`
     - `approximations`
   - Keep handicap data in `handicaps[]`; do not store round handicap values in `scores[]`.
4. Run a dry run:
   ```bash
   ./venv/bin/python scripts/process_tournament.py input/tournament_data.json --dry-run
   ```
5. Run the standalone audit whenever you want a quick canonical health check:
   ```bash
   ./venv/bin/python scripts/audit_canonical_data.py
   ```
6. Run the local ingest:
   ```bash
   ./venv/bin/python scripts/process_tournament.py input/tournament_data.json
   ```
7. Review local site output under `website/`.
   - Start with `website/DataAudit.html` to cross-check payouts, handicaps, and gross totals by date/player.
   - Then review `website/index.html` and the latest `website/results_*.html`.

## Safety Model

- `scripts/update_site.py` is local-only unless `--publish` is passed.
- `scripts/update_site.py` refreshes derived methodology data under `website/data/` as part of the local build.
- `scripts/process_tournament.py` only commits or pushes when explicitly asked.
- `scripts/ingest_data.py --dry-run` validates and simulates without mutating CSVs.
- Re-running the same tournament payload no longer duplicates payout rows in `data/financials.csv`.
- Corrected reruns update existing financial and handicap rows for the same canonical key instead of silently appending or skipping them.
- Post-ingest validation aborts before any write if duplicate canonical keys are detected in scores, financials, or handicaps.
- Score rows now require same-date handicap snapshots for every scored player; otherwise ingest aborts before write.
- Publish commands stage only `data/` and `website/`, and they abort if unrelated repo files are dirty.
- Ingest now prints a canonical audit checklist before any write and aborts by default if score rows are missing handicap snapshots or if handicap snapshots do not match a scored player/date.
- Financial rows without score rows are allowed, but they stay visible in the audit so payout-only events can still be reviewed.
- `--allow-incomplete` is available for intentional exceptions, but it should be rare and documented in `metadata.source_notes`.

## Recommended Commands

Validate only:

```bash
./venv/bin/python scripts/ingest_data.py input/tournament_data.json --dry-run
```

Canonical audit only:

```bash
./venv/bin/python scripts/audit_canonical_data.py
```

Validate plus full local processing:

```bash
./venv/bin/python scripts/process_tournament.py input/tournament_data.json
```

Local site rebuild only:

```bash
./venv/bin/python scripts/update_site.py
```

Explicit publish path:

```bash
./venv/bin/python scripts/update_site.py --publish
```
