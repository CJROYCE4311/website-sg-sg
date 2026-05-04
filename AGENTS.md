# SG@SG Golf Tournament Dashboard

## Purpose

This repo manages the SG@SG tournament data pipeline and static website.

Canonical data lives in:
- `data/scores.csv`
- `data/financials.csv`
- `data/handicaps.csv`
- `data/course_info.csv`
- `data/tournaments.csv`
- `data/team_pairings.csv`

Generated site output lives in `website/`.

## Preferred Driver

Codex is the primary driver for this repo. Keep the workflow LLM-agnostic where possible and avoid tool-specific assumptions in the operating docs.

Document roles:
- `README.md`: shortest operator quick start
- `AGENTS.md`: repo policy, guardrails, and runbook
- `docs/SGSG_Monthly_Tournament_Runbook.docx`: exact monthly operator checklist and responsibility map
- `docs/SQUABBIT_CSV_IMPORT.md`: technical Squabbit CSV import workflow
- `docs/CODEX_WORKFLOW.md`: compact detailed workflow

## Local Workflow

```
Squabbit CSV in Downloads -> CSV import/reconciliation -> reviewed JSON -> audit/dry-run -> canonical CSV upsert -> local site rebuild -> publish after approval
```

This clone is intended to run locally in parallel with the production deployment workflow.

- Default behavior is local only.
- Squabbit CSV export is the preferred raw source for completed tournaments.
- Screenshots are now a fallback source only when the CSV export is unavailable or needs manual verification.
- `scripts/import_squabbit_csv.py` converts Squabbit CSV exports into `input/tournament_data.from_squabbit.json`, reconciliation reports, `data/tournaments.csv`, and `data/team_pairings.csv`.
- `scripts/import_squabbit_csv.py --archive-source-csvs` moves successfully imported source CSV files from Downloads into `input/raw_exports/YYYY-MM-DD/`.
- `scripts/update_site.py` rebuilds the site without committing or pushing.
- `scripts/process_tournament.py` only commits or pushes if `--commit` or `--push` is explicitly passed.
- `scripts/ingest_data.py` updates existing financial and handicap rows when a repeat run carries corrected values for the same date/player key.
- `scripts/ingest_data.py` also flags handicap readings that are more than 1 standard deviation from a player's historical mean.
- `scripts/ingest_data.py` aborts before writing if duplicate canonical keys are detected in scores, financials, or handicaps.
- Publish commands stage only `data/` and `website/`, and they refuse to run if unrelated repo files are dirty.

## Monthly Operating Pattern

1. Chris downloads the completed Squabbit CSV export and leaves it in `/Users/chrisroyce/Downloads/`.
2. Codex imports the CSV, writes reconciliation reports, captures team pairings, and archives the source CSV locally:
   ```bash
   ./venv/bin/python scripts/import_squabbit_csv.py "/Users/chrisroyce/Downloads/SG@SG(<event>).csv" --tournaments-out data/tournaments.csv --archive-source-csvs
   ```
3. Review `input/squabbit_reconciliation_report.md` before ingest. Stop on unresolved identity conflicts, missing handicaps, incomplete team rows, payout reconciliation issues, or unexpected incoming-vs-canonical differences.
4. Run the canonical audit against the reviewed JSON:
   ```bash
   ./venv/bin/python scripts/audit_canonical_data.py --json-file input/tournament_data.from_squabbit.json
   ```
5. Validate without writing:
   ```bash
   ./venv/bin/python scripts/process_tournament.py input/tournament_data.from_squabbit.json --dry-run
   ```
6. Run the local update:
   ```bash
   ./venv/bin/python scripts/process_tournament.py input/tournament_data.from_squabbit.json
   ```
7. Review the affected pages and data outputs, especially:
   - `website/DataAudit.html`
   - `website/index.html`
   - the latest `website/results_*.html`
   - `website/MoneyList2026.html`
   - `website/PlayerStats.html`
   - `website/AverageScore.html`
   - `data/team_pairings.csv`
8. Only publish from this clone if Chris explicitly approves:
   ```bash
   ./venv/bin/python scripts/update_site.py --publish
   ```

## Entry Points

### `scripts/import_squabbit_csv.py`

```bash
./venv/bin/python scripts/import_squabbit_csv.py "/Users/chrisroyce/Downloads/SG@SG(<event>).csv" --tournaments-out data/tournaments.csv --archive-source-csvs
./venv/bin/python scripts/import_squabbit_csv.py "/Users/chrisroyce/Downloads/SG@SG(<event>).csv" --tournaments-out data/tournaments.csv --dry-run
```

### `scripts/process_tournament.py`

```bash
./venv/bin/python scripts/process_tournament.py input/tournament_data.from_squabbit.json
./venv/bin/python scripts/process_tournament.py input/tournament_data.from_squabbit.json --dry-run
./venv/bin/python scripts/process_tournament.py input/tournament_data.from_squabbit.json --skip-site-update
```

### `scripts/ingest_data.py`

```bash
./venv/bin/python scripts/ingest_data.py input/tournament_data.from_squabbit.json --dry-run
./venv/bin/python scripts/ingest_data.py input/tournament_data.from_squabbit.json
```

### `scripts/update_site.py`

```bash
./venv/bin/python scripts/update_site.py
./venv/bin/python scripts/update_site.py --publish
```

## Notes

- Plus handicaps are stored as negative values.
- Tournament year rolls November and December rounds into the following year.
- Repeat runs for the same payout payload do not duplicate `financials.csv`, and corrected reruns replace the prior value for that date/player/category key.
- Player display names from Squabbit are normalized before ingest; WHS IDs are stored only in the ignored local identity map at `input/identity/squabbit_players.csv`.
- If a tournament date already exists in canonical CSVs, canonical rows win over the Squabbit export so late player edits or unregistering in Squabbit do not rewrite history.
- Team pairings are captured in `data/team_pairings.csv`; once a date exists there, later imports preserve the existing team rows.
- The known April 5, 2025 Greg Funk and Todd Densley gross-score mismatches remain in `data/score_audit_exceptions.csv` and are excluded from gross-score analytics.
- `input/` is a local working area and is intentionally ignored by git.
- Raw Squabbit CSV exports archived under `input/raw_exports/` remain local and ignored by git.
- Use [website/DataAudit.html](/Users/chrisroyce/Golf/Tournaments/website-sg-sg/website/DataAudit.html) as the operator cross-check page for payouts, handicaps, and gross scores by player/date.
- See [docs/SGSG_Monthly_Tournament_Runbook.docx](/Users/chrisroyce/Golf/Tournaments/website-sg-sg/docs/SGSG_Monthly_Tournament_Runbook.docx) for the exact Chris/Codex monthly checklist.
- See [docs/SQUABBIT_CSV_IMPORT.md](/Users/chrisroyce/Golf/Tournaments/website-sg-sg/docs/SQUABBIT_CSV_IMPORT.md) for import details and reconciliation gates.
- See [docs/CODEX_WORKFLOW.md](/Users/chrisroyce/Golf/Tournaments/website-sg-sg/docs/CODEX_WORKFLOW.md) for the compact operating summary.
