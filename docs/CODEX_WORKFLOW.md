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

Generated:
- `website/index.html`
- `website/MoneyList2025.html`
- `website/MoneyList2026.html`
- `website/PlayerStats.html`
- `website/AverageScore.html`
- `website/HoleIndex.html`
- `website/HandicapAnalysis.html`
- `website/Handicap_Detail.html`
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
3. Merge those batches into a reviewed `input/tournament_data.json`.
4. Run a dry run:
   ```bash
   ./venv/bin/python scripts/process_tournament.py input/tournament_data.json --dry-run
   ```
5. Run the local ingest:
   ```bash
   ./venv/bin/python scripts/process_tournament.py input/tournament_data.json
   ```
6. Review local site output under `website/`.

## Safety Model

- `scripts/update_site.py` is local-only unless `--publish` is passed.
- `scripts/process_tournament.py` only commits or pushes when explicitly asked.
- `scripts/ingest_data.py --dry-run` validates and simulates without mutating CSVs.
- Re-running the same tournament payload no longer duplicates payout rows in `data/financials.csv`.

## Recommended Commands

Validate only:

```bash
./venv/bin/python scripts/ingest_data.py input/tournament_data.json --dry-run
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
