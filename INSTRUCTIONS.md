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

## Step 3: Tell Claude to Process

Open Claude Code in the `website-sg-sg` folder and say:

> "Process the tournament screenshots for [DATE]"

or simply:

> "Update the site with the new tournament data"

---

## Step 4: Review and Confirm

Claude will:
1. Read all the screenshots
2. Show you the extracted data for review
3. Ask you to confirm before processing

If anything looks wrong (score, name, amount), tell Claude and it will fix it.

---

## Step 5: Done

Once you confirm, Claude runs one command that:
- Validates the data
- Updates the database
- Regenerates the website
- Archives everything
- Pushes to GitHub

Netlify auto-deploys. Site is live within minutes.

---

## Quick Reference

| What | Where |
|------|-------|
| Drop screenshots | `input/screenshots/` |
| Archived screenshots | `input/processed/YYYY-MM-DD/` |
| Archived JSON | `input/history/YYYY-MM-DD.json` |
| Tournament date | Format as `YYYY-MM-DD` (e.g., `2026-02-21`) |
