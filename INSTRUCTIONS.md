# After Tournament: How to Update the Site

## Step 1: Collect Screenshots from Squabbit

Take screenshots of these screens (in any order):

| Screenshot | What to Capture |
|------------|-----------------|
| **Scorecards** | Each player's hole-by-hole scores (may need multiple screenshots if many players) |
| **Leaderboard** | Shows rankings, gross/net scores |
| **Payouts** | Best Ball, Quota, Net Medal amounts |
| **Skins** | Gross Skins and Net Skins winners/amounts |
| **Teams** | Partner pairings (if team game) |

**Tip:** Make sure player names and their handicap index (the number in parentheses) are visible.

---

## Step 2: Drop Screenshots in the Folder

Move all screenshots to:
```
website-sg-sg/input/screenshots/
```

---

## Step 3: Build the Weekly JSON

Use Codex to extract the screenshots in manageable batches:

- scorecards
- leaderboard / placements
- payouts / skins
- partner pairings and handicap indices

Consolidate the reviewed result into:

```
input/tournament_data.json
```

---

## Step 4: Validate First

Run:

```bash
./venv/bin/python scripts/process_tournament.py input/tournament_data.json --dry-run
```

If anything looks wrong, fix the JSON and rerun the dry run.

---

## Step 5: Done

Run:

```bash
./venv/bin/python scripts/process_tournament.py input/tournament_data.json
```

This will:
- Validates the data
- Updates the database
- Regenerates the website
- Archives everything

It does not commit or deploy unless you explicitly request that later.

---

## Quick Reference

| What | Where |
|------|-------|
| Drop screenshots | `input/screenshots/` |
| Archived screenshots | `input/processed/YYYY-MM-DD/` |
| Archived JSON | `input/history/YYYY-MM-DD.json` |
| Tournament date | Format as `YYYY-MM-DD` (e.g., `2026-02-21`) |
