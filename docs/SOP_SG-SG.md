# Standard Operating Procedure (SOP): SG@SG Dashboard Update Process

## 1. Project Structure

The project is organized to separate data, code, and content:

*   **`data/`**: Stores all Excel history (`YYYY-MM-DD_SG-SG_Data.xlsx`) and the Scorecard CSV.
*   **`website/`**: Contains the live HTML site.
    *   **`assets/`**: Stores images (logos, course photos).
*   **`scripts/`**: Stores the automation logic (`update_site.py`).
*   **`input/`**: The Agent's workspace.
    *   **`screenshots/`**: **DROP ZONE.** Place new tournament screenshots here.
    *   **`processed/`**: Archive for processed screenshots.
*   **`docs/`**: Documentation and SOPs.

## 2. The "Conductor" Workflow (Monthly Update)

### Step 1: Data Collection (User)
Take clear, scrolling screenshots of the results in Squabbit:

1.  **Gross Scores (Master List):** Capture the entire leaderboard (names + hole-by-hole scores). **Crucial:** Ensure the view includes the Handicap Index displayed next to the player name (e.g., `Jeff (0.5)`). This serves as the master list for both Scores and Handicaps.
    *   *Filenames:* `gross1.png`, `gross2.png`, etc.
2.  **Net Medal:** Capture the winners/payouts.
    *   *Filename:* `netmedal.png`
3.  **Skins (Gross & Net):** Capture the skin winners and payouts.
    *   *Filenames:* `grossskins.png`, `netskins.png`
4.  **Team Game (Quota/BB/Stableford):** Capture the team results/payouts.
    *   *Filenames:* `quota1.png`, `team1.png`, etc.

**Action:** Drag and drop these files into the `input/screenshots/` folder.

### Step 2: Agent Execution (AI)
Instruct the Agent: *"I have dropped the screenshots in input/screenshots. Please update the site."*

The Agent will perform the following "Conductor" Track:

1.  **Vision Extraction:** Read the screenshots in `input/screenshots/`.
2.  **Data Entry:** Extract scores, handicaps (converting `+` to negative numbers), and payouts to create a new Excel file: `data/YYYY-MM-DD_SG-SG_Data.xlsx`.
3.  **Execution:** Run the update script:
    ```bash
    python3 scripts/update_site.py
    ```
4.  **Cleanup:** Move used screenshots to `input/processed/YYYY-MM-DD/`.
5.  **Deployment:** Commit and push changes to GitHub.

### Step 3: Verification (User)
*   Check the live site (Netlify) to ensure the "Latest Results" writeup is accurate.
*   Verify the "Handicap Analysis" page shows the new round data.

## 3. Script Logic (`update_site.py`)

*   **Auto-Detection:** Automatically finds the latest Excel file in `data/` and uses the last 13 months of data.
*   **Calculations:**
    *   **Differentials:** `(Gross - 70.5) * 113 / 124`
    *   **Gap:** `Differential - Handicap Index` (Negative = Beat Index/Sandbagger Alert).
    *   **Implied Index:** Average of Best 3 / Best 6 differentials.
*   **Earnings Display:**
    *   **Team Games & Net Medal:** Displays **per-player** earnings (e.g., "Player A & Player B - $50" means $50 each).
    *   **Skins:** Displays individual skin totals.
*   **Deployment:** Automatically commits and pushes to `main`.

## 4. Troubleshooting

*   **"Blank" Analysis Page:** Ensure the `Handicaps` tab exists in the Excel file (or handicaps were extracted from Gross Scores) and the column is named `Handicap`.
*   **Plus Handicaps:** Ensure `+1.5` is stored as `-1.5` in the Excel file.
*   **Missing Images:** Ensure all images are in `website/assets/` and HTML links point to `assets/ImageName.png`.
