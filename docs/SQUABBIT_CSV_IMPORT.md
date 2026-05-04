# Squabbit CSV Import

Use Squabbit CSV exports as the raw source for completed tournaments. The importer converts one or more exports into the existing reviewed JSON shape, then the normal processor validates and ingests it.

## Monthly Website Update Flow

1. Download the completed tournament CSV from Squabbit:
   - Open the tournament in Squabbit.
   - Open the gear/settings menu.
   - Go to `Advanced` -> `Other` -> `Export as CSV`.

2. Import the exact downloaded CSV. Use the single new file for normal monthly updates:

   ```bash
   ./venv/bin/python scripts/import_squabbit_csv.py "/Users/chrisroyce/Downloads/SG@SG(<event>).csv" --tournaments-out data/tournaments.csv
   ```

   Batch imports are supported when rebuilding a season from multiple exports:

   ```bash
   ./venv/bin/python scripts/import_squabbit_csv.py "/Users/chrisroyce/Downloads/SG@SG"*.csv --tournaments-out data/tournaments.csv
   ```

3. Audit the generated reviewed JSON and the current canonical CSVs:

   ```bash
   ./venv/bin/python scripts/audit_canonical_data.py --json-file input/tournament_data.from_squabbit.json
   ```

4. Review the reconciliation report from the import:

   ```bash
   open input/squabbit_reconciliation_report.md
   ```

   The report is the monthly control point before ingest. Review `identity_conflicts`, `missing_handicaps`, `incomplete_team_rows`, `won_reconciliation_issues`, and any canonical reconciliation sections. For already-canonical dates, incoming Squabbit-only rows are reported and dropped. For new dates, resolve report issues before the ingest step.

5. Run the processor in dry-run mode. This validates the payload, simulates the canonical upsert, and runs the post-ingest audit without writing CSVs or website files:

   ```bash
   ./venv/bin/python scripts/process_tournament.py input/tournament_data.from_squabbit.json --dry-run
   ```

6. If the dry run is clean, run the normal local update. This updates canonical CSVs, archives the reviewed JSON, and regenerates the local website:

   ```bash
   ./venv/bin/python scripts/process_tournament.py input/tournament_data.from_squabbit.json
   ```

7. Review the generated website pages:
   - `website/DataAudit.html`
   - `website/index.html`
   - the latest `website/results_YYYY-MM-DD.html`
   - the affected dashboards such as `website/MoneyList2026.html`, `website/PlayerStats.html`, and `website/HoleIndex.html`

8. Publish only when the local website looks right:

   ```bash
   ./venv/bin/python scripts/update_site.py --publish
   ```

   Publishing stages only `data/` and `website/`, commits them, and pushes. It refuses to run if unrelated repo files are dirty.

## Conflict Policy

- Player display names from Squabbit are normalized before ingest.
- Quoted nicknames, such as `Robert Hill "Captain "`, are removed.
- WHS IDs are stored only in the local ignored identity map at `input/identity/squabbit_players.csv`.
- If a tournament date already exists in canonical CSVs, canonical rows win over the export. This protects against players unregistering, deleting themselves, changing nicknames, or later editing Squabbit data after the event.
- For new dates, the Squabbit export is used as the source of scores, handicaps, team placements, skins, and payout categories.
- Gross score must equal the sum of holes. New mismatches fail validation or the post-ingest audit unless explicitly listed in `data/score_audit_exceptions.csv`.
- Unresolved gross-score exceptions stay in canonical history and DataAudit, but are excluded from scoring analytics such as handicap analysis, player stats, average score, hole index, and methodology data.

## Useful Outputs

- `input/tournament_data.from_squabbit.json`: reviewed JSON payload for the existing ingest workflow.
- `input/identity/squabbit_players.csv`: local-only WHS/name identity map.
- `input/squabbit_reconciliation_report.md`: human-readable import reconciliation report.
- `input/squabbit_reconciliation_report.json`: machine-readable import reconciliation report.
- `data/tournaments.csv`: safe event metadata by date and season.

## Reconciliation Gates

Before ingesting a new monthly tournament, stop and resolve these items from `input/squabbit_reconciliation_report.md`:

- `identity_conflicts`: WHS ID maps to a different canonical player than before.
- `missing_handicaps`: a scored player has no handicap in the export.
- `players_missing_from_players_section`: scorecard data names a player not present in the Players section.
- `incomplete_team_rows`: Squabbit exported a team row without complete players/results.
- `won_reconciliation_issues`: derived category payouts do not reconcile to Squabbit's player `Won` total.
- Any validation failure from `process_tournament.py --dry-run`, especially gross score not equal to the H1-H18 total.

For a date that already exists in canonical CSVs, the importer reports canonical differences and keeps canonical. For a new date, the report is the review queue before data becomes canonical.

## Current Historical Score Exceptions

Two April 5, 2025 records from the 2025 tournament year are retained as unresolved historical exceptions because no April 5 Squabbit CSV, reviewed JSON, or source screenshot is available locally:

- Greg Funk: canonical gross `79`, H1-H18 total `76`.
- Todd Densley: canonical gross `73`, H1-H18 total `77`.

Those exceptions are documented in `data/score_audit_exceptions.csv` and excluded from gross-score analytics. If the original source is recovered, correct either the hole values or gross score in `data/scores.csv`, mark the exception row `resolved` or remove it, and run:

```bash
./venv/bin/python scripts/update_site.py
./venv/bin/python scripts/audit_canonical_data.py
```
