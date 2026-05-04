# Codex Workflow

## Goal

Run this directory as a local parallel-processing clone that can:
- import completed Squabbit tournament CSV exports
- reconcile Squabbit output against canonical history
- maintain the canonical CSV files
- capture monthly team pairings for future team analytics
- regenerate the site locally
- avoid commit and deploy side effects by default

## Canonical vs Generated Files

Canonical:
- `data/scores.csv`
- `data/financials.csv`
- `data/handicaps.csv`
- `data/course_info.csv`
- `data/tournaments.csv`
- `data/team_pairings.csv`
- `data/score_audit_exceptions.csv`
- `data/player_aliases.json`

Canonical notes:
- `scores.csv` stores player performance for the round, including `Differential`.
- `handicaps.csv` stores the handicap snapshot for the date, including `Handicap_Index` and `Course_Handicap`.
- `financials.csv` may stand alone when payout screenshots are preserved but later score rows disappear in Squabbit.
- `tournaments.csv` stores safe event metadata by date and season.
- `team_pairings.csv` stores date/team/player pairings, rank, score, payout, and source file. Once a date exists there, later Squabbit imports preserve the existing rows.
- `score_audit_exceptions.csv` stores explicit gross-score audit exceptions. The April 5, 2025 Greg Funk and Todd Densley rows are retained in history but excluded from gross-score analytics.
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
- `input/tournament_data.from_squabbit.json`
- `input/squabbit_reconciliation_report.md`
- `input/squabbit_reconciliation_report.json`
- `input/identity/squabbit_players.csv`
- `input/raw_exports/`

## Monthly Operating Pattern

1. Chris downloads the completed Squabbit CSV export and leaves it in `/Users/chrisroyce/Downloads/`.
2. Import the exact Squabbit CSV:
   ```bash
   ./venv/bin/python scripts/import_squabbit_csv.py "/Users/chrisroyce/Downloads/SG@SG(<event>).csv" --tournaments-out data/tournaments.csv --archive-source-csvs
   ```
3. Review `input/squabbit_reconciliation_report.md`.
   - Stop on unresolved identity conflicts.
   - Stop on missing handicaps for scored players.
   - Stop on incomplete team rows unless resolved from Squabbit/canonical data.
   - Review payout reconciliation issues before ingest.
   - For already-canonical dates, canonical rows remain authoritative.
4. Run the canonical audit against the reviewed import:
   ```bash
   ./venv/bin/python scripts/audit_canonical_data.py --json-file input/tournament_data.from_squabbit.json
   ```
5. Run a dry run:
   ```bash
   ./venv/bin/python scripts/process_tournament.py input/tournament_data.from_squabbit.json --dry-run
   ```
6. Run the standalone audit whenever you want a quick canonical health check:
   ```bash
   ./venv/bin/python scripts/audit_canonical_data.py
   ```
7. Run the local ingest:
   ```bash
   ./venv/bin/python scripts/process_tournament.py input/tournament_data.from_squabbit.json
   ```
8. Review local site output under `website/`.
   - Start with `website/DataAudit.html` to cross-check payouts, handicaps, and gross totals by date/player.
   - Then review `website/index.html` and the latest `website/results_*.html`.
   - Review `website/MoneyList2026.html`, `website/PlayerStats.html`, `website/AverageScore.html`, and `data/team_pairings.csv`.

Screenshots remain a fallback source only if the CSV export is unavailable or a specific Squabbit screen needs manual verification. For screenshot fallback payloads, start from `docs/tournament_data.template.json` and keep handicap data in `handicaps[]`.

## Safety Model

- `scripts/update_site.py` is local-only unless `--publish` is passed.
- `scripts/update_site.py` refreshes derived methodology data under `website/data/` as part of the local build.
- `scripts/import_squabbit_csv.py --archive-source-csvs` moves successfully imported source CSVs into ignored local archives under `input/raw_exports/YYYY-MM-DD/`.
- WHS IDs stay only in the ignored local identity map at `input/identity/squabbit_players.csv`.
- Squabbit player nicknames are normalized before ingest.
- Existing canonical rows win over repeat Squabbit imports for the same date, protecting against late player edits or accidental unregistering.
- Existing `data/team_pairings.csv` rows win over repeat Squabbit imports for the same date.
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

Import the Squabbit CSV:

```bash
./venv/bin/python scripts/import_squabbit_csv.py "/Users/chrisroyce/Downloads/SG@SG(<event>).csv" --tournaments-out data/tournaments.csv --archive-source-csvs
```

Validate only:

```bash
./venv/bin/python scripts/process_tournament.py input/tournament_data.from_squabbit.json --dry-run
```

Canonical audit only:

```bash
./venv/bin/python scripts/audit_canonical_data.py
```

Validate plus full local processing:

```bash
./venv/bin/python scripts/process_tournament.py input/tournament_data.from_squabbit.json
```

Local site rebuild only:

```bash
./venv/bin/python scripts/update_site.py
```

Explicit publish path:

```bash
./venv/bin/python scripts/update_site.py --publish
```
