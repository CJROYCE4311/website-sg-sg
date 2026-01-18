# Standard Operating Procedure (SOP): SG@SG Dashboard Update Process

## 1. Project Structure

The project is organized to separate data, code, and content:

*   **`data/`**: Source of Truth. Contains the CSV databases:
    *   `scores.csv`: Player scores, handicaps, partners, and rankings.
    *   `financials.csv`: Winnings and payouts.
    *   `handicaps.csv`: Historical handicap index data.
*   **`website/`**: Contains the live HTML site (`index.html`, `PlayerStats.html`, etc.).
    *   **`assets/`**: Stores images (logos, course photos).
*   **`scripts/`**: Automation logic.
    *   `ingest_data.py`: Handles JSON input, batch processing, and database upserts.
    *   `update_site.py`: Generates HTML pages and updates the leaderboard.
*   **`input/`**: The Agent's workspace.
    *   **`screenshots/`**: **DROP ZONE.** Place new tournament screenshots here.
    *   **`processed/`**: Archive for processed screenshots.
*   **`docs/`**: Documentation and SOPs.

## 2. The "Conductor" Workflow (Monthly Update)

### Step 1: Data Collection (User)
Take clear, scrolling screenshots of the results in Squabbit:

1.  **Gross Scores (Master List):** Capture the entire leaderboard (names + hole-by-hole scores). **Crucial:** Ensure the view includes the Handicap Index displayed next to the player name (e.g., `Jeff (0.5)`).
    *   *Filenames:* `gross1.png`, `gross2.png`, etc.
2.  **Net Medal / Rankings:** Capture the winners/payouts and any specific "Net" or "Gross" rankings.
    *   *Filename:* `netmedal.png`
3.  **Skins (Gross & Net):** Capture the skin winners and payouts.
    *   *Filenames:* `grossskins.png`, `netskins.png`
4.  **Team Game:** Capture the team results, payouts, and **partners**.
    *   *Filenames:* `quota1.png`, `team1.png`, etc.

**Action:** Drag and drop these files into the `input/screenshots/` folder.

### Step 2: Agent Execution (AI)
Instruct the Agent: *"I have dropped the screenshots in input/screenshots. Please update the site."*

The Agent will perform the following "Conductor" Track:

1.  **Vision Extraction:** Read the screenshots in `input/screenshots/`.
2.  **Data Extraction:** Extract:
    *   Scores & Handicaps (converting `+` to negative numbers).
    *   **Financials:** Payout amounts per category.
    *   **Meta Data:** Partners, Team Ranks, and Individual Ranks.
3.  **Ingestion:** Create a JSON payload (supporting `update_batch` for multiple dates) and run:
    ```bash
    python3 scripts/ingest_data.py <input.json>
    ```
    *   *Note:* The script uses **Upsert** logic. It updates existing records with new details (like Partners/Ranks) without creating duplicates.
4.  **Site Generation:** The ingestion script automatically triggers `update_site.py`.
5.  **Cleanup:** Move used screenshots to `input/processed/YYYY-MM-DD/`.
6.  **Deployment:** Commit and push changes to GitHub.

### Step 3: Verification (User)
*   **Homepage:** Check "Latest Results" for correct Team/Net placements (e.g., "1: Scott Lucas").
*   **Player Stats:** Verify the "Player Metrics" gauge visuals.
*   **Analysis:** Verify the "Handicap Analysis" page shows the new round.

## 3. Script Logic (`update_site.py`)

*   **Source:** Reads directly from `data/*.csv`.
*   **Calculations:**
    *   **Differentials:** `(Gross - 70.5) * 113 / 124`
    *   **Gap:** `Differential - Handicap Index` (Negative = Beat Index).
*   **Writeups:**
    *   **Merged Data:** Combines Financials with Score data to display Rankings and Partners in the results feed.
    *   **Format:** Lists one team/player per line for readability.
*   **Deployment:** Automatically commits and pushes to `main`.

## 4. Troubleshooting

*   **Duplicate Names:** If names appear twice (e.g., "Steve McCormick" vs "Steve Mccormick"), ask the Agent to run a normalization step to fix capitalization and merge records.
*   **Missing Ranks:** If placements are missing in the recap, provide the Agent with the specific rankings to "Upsert" into the database.
*   **"Blank" Analysis Page:** Ensure the `Handicaps` column in CSV is populated.
*   **Visual Glitches:** If gauges look wrong, ensure `PlayerStats.html` has the latest JS logic for the 3-segment color arc.
