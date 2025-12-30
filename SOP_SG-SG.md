# Standard Operating Procedure (SOP): SG@SG Dashboard Update Process

## 1. Data Collection (The "Screenshot" Method)

Instead of fighting with Squabbit's locked data, we use a visual extraction workflow.

### Required Screenshots
Take clear, scrolling screenshots of the following tabs in Squabbit and save them to a new folder (e.g., `YYYY-MM-DD_Results`):

1.  **Gross Scores:** Capture the entire leaderboard (names + hole-by-hole scores).
    *   *Filenames:* `gross1.png`, `gross2.png`, etc.
2.  **Handicaps:** Capture the player list showing Handicap Indexes (HI).
    *   *Filenames:* `handicap1.png`, etc.
3.  **Net Medal:** Capture the winners/payouts.
    *   *Filename:* `netmedal.png`
4.  **Skins (Gross & Net):** Capture the skin winners and payouts.
    *   *Filenames:* `grossskins.png`, `netskins.png`
5.  **Team Game (Quota/BB):** Capture the team results/payouts.
    *   *Filenames:* `quota1.png`, etc.

## 2. AI Processing (The "Agent" Method)

1.  **Upload:** Provide the folder of screenshots to the AI Agent.
2.  **Command:** Instruct the Agent: *"Extract data from these screenshots and generate the Excel file for the [Date] tournament."*
3.  **Verification:** The Agent will:
    *   OCR the player names and scores.
    *   Extract handicaps (converting "+" handicaps to negative numbers, e.g., +1.7 -> -1.7).
    *   Extract payouts and team assignments.
    *   Generate a standard Excel file: `YYYY-MM-DD_SG-SG_Data.xlsx`.

## 3. Automated Pipeline Execution

Once the Excel file is generated, the AI Agent (or you) runs the pipeline script.

```bash
python3 update_site.py
```

### What the Script Does:
*   **13-Month Lookback:** automatically filters historical data to the last 13 months for relevant analysis.
*   **Column Normalization:** Automatically maps `HI`, `Handicap Index` -> `Handicap` for consistency.
*   **Calculations:**
    *   **Differentials:** `(Gross - 70.5) * 113 / 124`
    *   **Gap:** `Handicap Used - Differential`
    *   **Implied Index:** Average of Best 3 / Best 6 differentials.
*   **Updates Dashboards:**
    *   `index.html` (Latest Results Writeup)
    *   `MoneyList2025/2026.html`
    *   `HandicapAnalysis.html` (Scatter plots & Tables)
    *   `Handicap_Detail.html` (Round-by-round detail)
    *   `AverageScore.html` (Hole difficulty)

## 4. Deployment

The script automatically commits and pushes changes to GitHub. Netlify detects the push and deploys the site live within seconds.

## Troubleshooting

*   **"Blank" Analysis Page:** Ensure `Handicaps` tab exists in the Excel file and column is named `HI` or `Handicap`.
*   **New Players:** If a new player appears, ensure their name spelling matches exactly across all screenshots.
*   **Plus Handicaps:** Ensure they are stored as NEGATIVE numbers in the Excel file (e.g., -2.0) for the math to work (Net = Gross - Hcp).