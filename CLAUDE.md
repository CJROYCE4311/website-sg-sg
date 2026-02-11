# SG@SG Golf Tournament Dashboard

## Project Overview

This is a golf tournament dashboard for the Saturday Game at Sterling Grove (SG@SG). It tracks player scores, handicaps, financials, and generates a static website hosted on Netlify.

**Live Site:** Deployed via Netlify on push to `main` branch.

## Tournament Data Workflow

```
Screenshots (Squabbit) → Claude extracts data → JSON → Python Scripts → CSV Updates → Website Generation → Git Push
```

### Step-by-Step Process

1. **User drops screenshots** into `input/screenshots/`
2. **Claude reads screenshots** and extracts:
   - Player names with handicap indices (e.g., "Jeff (0.5)")
   - Hole-by-hole scores from scorecards
   - Payout amounts by category
   - Partners and rankings
3. **Claude creates JSON** matching the schema below
4. **Run processing script:**
   ```bash
   ./venv/bin/python scripts/process_tournament.py input/tournament_data.json --commit --push
   ```
5. Script automatically:
   - Validates data (gross score = sum of holes, handicap range, etc.)
   - Ingests into CSVs with upsert logic
   - Archives JSON to `input/history/YYYY-MM-DD.json`
   - Moves screenshots to `input/processed/YYYY-MM-DD/`
   - Regenerates all website pages
   - Commits and pushes to GitHub

## JSON Schema

```json
{
  "date": "YYYY-MM-DD",
  "scores": [
    {
      "Player": "Name",
      "H1": 5, "H2": 4, "H3": 3, ..., "H18": 5,
      "Gross_Score": 82,
      "Round_Handicap": 10.5,
      "Partner": "Partner Name",
      "Team_Rank": "1",
      "Individual_Rank": "T3"
    }
  ],
  "financials": [
    { "Player": "Name", "Category": "BestBall", "Amount": 120.0 }
  ],
  "handicaps": [
    { "Player": "Name", "Handicap_Index": 10.5 }
  ]
}
```

**Valid financial categories:** `BestBall`, `Quota`, `NetMedal`, `GrossSkins`, `NetSkins`

## Key Constants

| Constant | Value |
|----------|-------|
| Course Rating | 70.5 |
| Slope | 124 |
| Par | 72 |
| Plus handicaps | Stored as negative (e.g., -1.7) |
| Tournament Year | Nov/Dec rounds count toward next year |

## Directory Structure

```
website-sg-sg/
├── data/
│   ├── scores.csv          # Hole-by-hole scores, handicaps, partners, rankings
│   ├── financials.csv      # Payouts by category
│   ├── handicaps.csv       # Historical handicap index tracking
│   └── course_info.csv     # Course par, slope, yardage per hole
├── input/
│   ├── screenshots/        # Drop new screenshots here
│   ├── processed/          # Archived screenshots by date
│   └── history/            # Archived JSON payloads by date
├── scripts/
│   ├── process_tournament.py  # Single entry point (recommended)
│   ├── ingest_data.py         # Data validation and CSV ingestion
│   └── update_site.py         # Website regeneration
├── website/
│   ├── index.html             # Homepage with latest results
│   ├── MoneyList2026.html     # Current year money list
│   ├── MoneyList2025.html     # Previous year money list
│   ├── PlayerStats.html       # Player statistics
│   ├── AverageScore.html      # Hole averages
│   ├── HoleIndex.html         # Hole difficulty index
│   ├── HandicapAnalysis.html  # Handicap audit (admin only)
│   ├── Handicap_Detail.html   # Detailed round history (admin only)
│   ├── AdminPortal.html       # Password-protected admin access
│   └── results_*.html         # Individual tournament recap pages
└── venv/                      # Python virtual environment
```

## Key Scripts

### `scripts/process_tournament.py` (Recommended)

Single command for full workflow:

```bash
# Process only (no git)
./venv/bin/python scripts/process_tournament.py input/tournament_data.json

# Process + commit
./venv/bin/python scripts/process_tournament.py input/tournament_data.json --commit

# Process + commit + push (full workflow)
./venv/bin/python scripts/process_tournament.py input/tournament_data.json --commit --push

# Skip screenshot archiving
./venv/bin/python scripts/process_tournament.py input/tournament_data.json --no-archive-screenshots
```

### `scripts/ingest_data.py`

Lower-level ingestion with validation:

```bash
./venv/bin/python scripts/ingest_data.py input/tournament_data.json
./venv/bin/python scripts/ingest_data.py input/tournament_data.json --skip-validation
```

### `scripts/update_site.py`

Regenerates all website pages from CSV data. Automatically called by ingest script.

```bash
./venv/bin/python scripts/update_site.py
```

## Data Validation

The ingestion script validates:
- `Gross_Score` equals sum of H1-H18
- `Round_Handicap` between -10 and 54
- Required fields present (`Player`, `Gross_Score`, etc.)
- No duplicate players per tournament date
- Valid financial categories
- No negative payout amounts

Validation errors abort ingestion to prevent bad data.

## Website Features

### Public Pages
- **Homepage:** Latest tournament results, upcoming dates
- **Money Lists:** 2025 and 2026 earnings by player
- **Player Stats:** Average gross/net scores
- **Average Score:** Scoring average by hole
- **Hole Index:** Hole difficulty ranking
- **Results Log:** Links to individual tournament recaps

### Admin-Only Pages (behind password)
- **Handicap Analysis:** Audit of implied vs actual handicaps
- **Detailed Round History:** All rounds per player
- **Methodology Report:** Handicap calculation methodology
- **Handicap Proposal:** Fairer competition proposal

## Screenshot Tips

When extracting from Squabbit screenshots, look for:
- **Scorecards:** Player name, handicap in parentheses, hole-by-hole scores
- **Leaderboard:** Gross/Net rankings, team pairings
- **Payouts:** Category (Best Ball, Quota, Skins) and amounts
- **Partners:** Who played with whom for team games

## Troubleshooting

### Validation Error: Gross score mismatch
Double-check the hole-by-hole extraction. Common issues:
- Misread digit (6 vs 8, 4 vs 9)
- Skipped a hole
- Wrong player's scores

### Duplicate entries
The ingest script uses upsert logic - same player + same date will update existing record.

### Results log duplicating
Fixed by using HTML comment markers. If it happens again, check that `<!-- RESULTS-LOG-START -->` and `<!-- RESULTS-LOG-END -->` markers exist in `index.html`.
