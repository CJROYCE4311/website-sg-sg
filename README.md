# SG@SG Monthly Processing

This is the main operator guide for updating the SG@SG data and website.

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
4. Run validation and present handicap readings that are more than 1 standard deviation above or below that player's historical mean.
5. Wait for your review if anything looks questionable.
6. Update the canonical files:
   - `data/scores.csv`
   - `data/financials.csv`
   - `data/handicaps.csv`
7. Rebuild the local website output, including:
   - `website/index.html`
   - money list pages
   - handicap analysis pages
   - player metric pages
   - tournament recap pages

## Monthly Processing Commands

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
- any player name that looks new or inconsistent

## Canonical Files

The source-of-truth files are:
- `data/scores.csv`
- `data/financials.csv`
- `data/handicaps.csv`
- `data/course_info.csv`

The generated website files are under:
- `website/`

## Notes

- Stableford individual results currently roll into the money list through the `NetMedal` category, but the recap display can still show `Stableford`.
- By default this repo works locally only. Commit, push, and deploy happen only when explicitly requested.
- The main local workflow docs are also in `AGENTS.md`.
