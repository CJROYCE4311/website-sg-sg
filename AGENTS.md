# SG@SG Golf Tournament Dashboard

## Purpose

This repo manages the SG@SG tournament data pipeline and static website.

Canonical data lives in:
- `data/scores.csv`
- `data/financials.csv`
- `data/handicaps.csv`
- `data/course_info.csv`

Generated site output lives in `website/`.

## Preferred Driver

Codex is the primary driver for this repo. Keep the workflow LLM-agnostic where possible and avoid tool-specific assumptions in the operating docs.

Document roles:
- `README.md`: shortest operator quick start
- `AGENTS.md`: repo policy, guardrails, and runbook
- `docs/CODEX_WORKFLOW.md`: compact detailed workflow
- `docs/WORKFLOW_VISUAL.html`: swim-lane and output map

## Local Workflow

```
Screenshots (Squabbit) -> staged extraction -> reviewed JSON -> CSV upsert -> local site rebuild
```

This clone is intended to run locally in parallel with the production deployment workflow.

- Default behavior is local only.
- `scripts/update_site.py` rebuilds the site without committing or pushing.
- `scripts/process_tournament.py` only commits or pushes if `--commit` or `--push` is explicitly passed.
- `scripts/ingest_data.py` updates existing financial and handicap rows when a repeat run carries corrected values for the same date/player key.
- `scripts/ingest_data.py` also flags handicap readings that are more than 1 standard deviation from a player's historical mean.
- `scripts/ingest_data.py` aborts before writing if duplicate canonical keys are detected in scores, financials, or handicaps.
- Publish commands stage only `data/` and `website/`, and they refuse to run if unrelated repo files are dirty.

## Weekly Operating Pattern

1. Drop new screenshots into `input/screenshots/`.
2. Extract the week in stages:
   - scorecards and gross totals
   - leaderboard ranks and partners
   - payouts and skins
   - handicap index list
3. Consolidate the reviewed output into `input/tournament_data.json`.
   - Start from `docs/tournament_data.template.json` so metadata is always included.
4. Validate without writing:
   ```bash
   ./venv/bin/python scripts/process_tournament.py input/tournament_data.json --dry-run
   ```
5. Run the local update:
   ```bash
   ./venv/bin/python scripts/process_tournament.py input/tournament_data.json
   ```
6. Review the affected pages in `website/`, especially:
   - `website/DataAudit.html`
   - `website/index.html`
   - the latest `website/results_*.html`
7. Only publish from this clone if you explicitly choose to:
   ```bash
   ./venv/bin/python scripts/update_site.py --publish
   ```

## Entry Points

### `scripts/process_tournament.py`

```bash
./venv/bin/python scripts/process_tournament.py input/tournament_data.json
./venv/bin/python scripts/process_tournament.py input/tournament_data.json --dry-run
./venv/bin/python scripts/process_tournament.py input/tournament_data.json --skip-site-update
```

### `scripts/ingest_data.py`

```bash
./venv/bin/python scripts/ingest_data.py input/tournament_data.json --dry-run
./venv/bin/python scripts/ingest_data.py input/tournament_data.json
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
- `input/` is a local working area and is intentionally ignored by git.
- Use [website/DataAudit.html](/Users/chrisroyce/Golf/Tournaments/website-sg-sg/website/DataAudit.html) as the operator cross-check page for payouts, handicaps, and gross scores by player/date.
- See [docs/CODEX_WORKFLOW.md](/Users/chrisroyce/Golf/Tournaments/website-sg-sg/docs/CODEX_WORKFLOW.md) for the compact operating summary.
