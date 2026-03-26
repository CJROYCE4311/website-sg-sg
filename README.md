# SG@SG Operator Quick Start

This is the shortest operator guide for updating SG@SG data and rebuilding the website locally.

For the full repo policy and workflow details, also see:
- [AGENTS.md](/Users/chrisroyce/Developer/Personal_Projects/website-sg-sg/AGENTS.md)
- [docs/CODEX_WORKFLOW.md](/Users/chrisroyce/Developer/Personal_Projects/website-sg-sg/docs/CODEX_WORKFLOW.md)
- [docs/WORKFLOW_VISUAL.html](/Users/chrisroyce/Developer/Personal_Projects/website-sg-sg/docs/WORKFLOW_VISUAL.html)

## What You Do

1. Put the new screenshots in:
   `input/screenshots/`
2. Include screenshots for:
   - gross by-hole scores for all players
   - team data for all teams
   - individual results only if the player finishes in the money
   - skins and payout screens when available
3. Tell Codex to process the new batch.

## What Codex Will Do

1. Read the screenshots in stages so larger weeks do not hit model limits.
2. Extract:
   - player names
   - handicap indices
   - by-hole gross scores
   - team pairings and team placements
   - individual in-the-money results
   - skins and payouts
3. Build or update:
   `input/tournament_data.json`
   Start from:
   `docs/tournament_data.template.json`
4. Run validation and present handicap readings that are more than 1 standard deviation above or below that player's historical mean.
5. Run automated post-ingest key validation so canonical files cannot be written with duplicate score, financial, or handicap keys.
6. Wait for your review if anything looks questionable.
7. Update the canonical files:
   - `data/scores.csv`
   - `data/financials.csv`
   - `data/handicaps.csv`
8. Rebuild the local website output, including:
   - `website/index.html`
   - money list pages
   - handicap analysis pages
   - player metric pages
   - tournament recap pages

## Processing Commands

Validate only:

```bash
./venv/bin/python scripts/process_tournament.py input/tournament_data.json --dry-run
```

Process and rebuild locally:

```bash
./venv/bin/python scripts/process_tournament.py input/tournament_data.json
```

Rebuild the site only:

```bash
./venv/bin/python scripts/update_site.py
```

## Expected Review Step

Before final processing, review:
- handicap outliers flagged by the script
- team pairings
- individual in-the-money results
- payout amounts
- gross score totals by player
- [website/DataAudit.html](/Users/chrisroyce/Developer/Personal_Projects/website-sg-sg/website/DataAudit.html) for payouts, handicaps, and gross totals by date/player
- any player name that looks new or inconsistent

For repeatable payload structure, use:
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

The generated website files are under:
- `website/`

The main operator validation page is:
- `website/DataAudit.html`

## Notes

- Stableford individual results currently roll into the money list through the `NetMedal` category, but the recap display can still show `Stableford`.
- Re-running the same month with corrected payout or handicap values now updates the existing canonical row instead of creating duplicates or ignoring the correction.
- The ingest step now aborts before writing if it detects duplicate canonical keys in scores, financials, or handicaps.
- Publish commands now stage only `data/` and `website/`, and they abort if unrelated repo files are dirty.
- By default this repo works locally only. Commit, push, and deploy happen only when explicitly requested.
- `README.md` is the quick start, `AGENTS.md` is the repo policy/runbook, and `docs/CODEX_WORKFLOW.md` is the compact detailed workflow.
