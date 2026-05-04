# SG@SG Operator Quick Start

This is the shortest operator guide for updating SG@SG data and rebuilding the website locally.

For the full repo policy and workflow details, also see:
- [AGENTS.md](/Users/chrisroyce/Golf/Tournaments/website-sg-sg/AGENTS.md)
- [docs/SGSG_Monthly_Tournament_Runbook.docx](/Users/chrisroyce/Golf/Tournaments/website-sg-sg/docs/SGSG_Monthly_Tournament_Runbook.docx)
- [docs/SQUABBIT_CSV_IMPORT.md](/Users/chrisroyce/Golf/Tournaments/website-sg-sg/docs/SQUABBIT_CSV_IMPORT.md)
- [docs/CODEX_WORKFLOW.md](/Users/chrisroyce/Golf/Tournaments/website-sg-sg/docs/CODEX_WORKFLOW.md)

## What You Do

1. Open the completed tournament in Squabbit.
2. Download the tournament CSV export from Advanced -> Other -> Export as CSV.
3. Leave the downloaded CSV in `/Users/chrisroyce/Downloads/`.
4. Tell Codex the tournament date and that the Squabbit CSV is ready to process.
5. Review any reconciliation questions and approve publish only after the local website review.

## What Codex Will Do

1. Find the target SG@SG CSV in Downloads.
2. Import it with `scripts/import_squabbit_csv.py`.
3. Write:
   - `input/tournament_data.from_squabbit.json`
   - `input/squabbit_reconciliation_report.md`
   - `data/tournaments.csv`
   - `data/team_pairings.csv`
4. Archive the raw Squabbit CSV under `input/raw_exports/YYYY-MM-DD/`.
5. Normalize Squabbit display names and preserve canonical rows for existing dates.
6. Run the canonical audit and dry run before writing.
7. Wait for your review if anything looks questionable.
8. Update the canonical files:
   - `data/scores.csv`
   - `data/financials.csv`
   - `data/handicaps.csv`
9. Rebuild the local website output, including:
   - `website/index.html`
   - money list pages
   - handicap analysis pages
   - player metric pages
   - tournament recap pages
10. Publish only after explicit approval.

## Processing Commands

Import the Squabbit CSV:

```bash
./venv/bin/python scripts/import_squabbit_csv.py "/Users/chrisroyce/Downloads/SG@SG(<event>).csv" --tournaments-out data/tournaments.csv --archive-source-csvs
```

Audit the reviewed import:

```bash
./venv/bin/python scripts/audit_canonical_data.py --json-file input/tournament_data.from_squabbit.json
```

Validate only:

```bash
./venv/bin/python scripts/process_tournament.py input/tournament_data.from_squabbit.json --dry-run
```

Process and rebuild locally:

```bash
./venv/bin/python scripts/process_tournament.py input/tournament_data.from_squabbit.json
```

Rebuild the site only:

```bash
./venv/bin/python scripts/update_site.py
```

## Expected Review Step

Before final processing, review:
- `input/squabbit_reconciliation_report.md`
- handicap outliers flagged by the script
- team pairings
- individual in-the-money results
- payout amounts
- gross score totals by player
- [website/DataAudit.html](/Users/chrisroyce/Golf/Tournaments/website-sg-sg/website/DataAudit.html) for payouts, handicaps, and gross totals by date/player
- any player name that looks new or inconsistent
- `data/team_pairings.csv` for monthly team history

If the Squabbit CSV is unavailable and screenshots must be used as a fallback, use:
- `docs/tournament_data.template.json`

Template notes:
- keep handicap data in `handicaps[]`, not in `scores[]`
- `scores[]` should carry gross totals, partners, and ranks
- `metadata` should always include:
  - `full_scorecard_available`
  - `handicap_list_available`
  - `screenshots`
  - `source_notes`
  - `approximations`

## Canonical Files

The source-of-truth files are:
- `data/scores.csv`
- `data/financials.csv`
- `data/handicaps.csv`
- `data/course_info.csv`
- `data/tournaments.csv`
- `data/team_pairings.csv`

The generated website files are under:
- `website/`

The main operator validation page is:
- `website/DataAudit.html`

## Notes

- Stableford individual results currently roll into the money list through the `NetMedal` category, but the recap display can still show `Stableford`.
- The Squabbit CSV export is now the preferred raw source for completed tournaments.
- Re-running the same month with corrected payout or handicap values now updates the existing canonical row instead of creating duplicates or ignoring the correction.
- Team pairings are preserved by date once written to `data/team_pairings.csv`.
- Raw Squabbit CSV exports archived under `input/raw_exports/` stay local and ignored by git.
- The ingest step now aborts before writing if it detects duplicate canonical keys in scores, financials, or handicaps.
- Publish commands now stage only `data/` and `website/`, and they abort if unrelated repo files are dirty.
- By default this repo works locally only. Commit, push, and deploy happen only when explicitly requested.
- `README.md` is the quick start, `AGENTS.md` is the repo policy/runbook, `docs/SGSG_Monthly_Tournament_Runbook.docx` is the monthly checklist, and `docs/CODEX_WORKFLOW.md` is the compact detailed workflow.
