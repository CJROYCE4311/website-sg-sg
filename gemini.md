# Standard Operating Procedure (SOP): SG@SG Dashboard Update Process

## 🚨 HIGH PRIORITY: NEXT STEPS (Paused Task)
**Task:** Extract Raw Score Data from Squabbit (Flutter App).
**Method:** Plan A - Network Sniffer (Preferred over OCR).

**Instructions:**
1.  **Open Developer Tools:** In Chrome/Safari, press `Cmd + Option + I` (Mac).
2.  **Network Tab:** Go to "Network" tab, filter by "Fetch/XHR".
3.  **Trigger Data:** Refresh the Squabbit leaderboard page.
4.  **Find Payload:** Look for a request named `leaderboard`, `scores`, or similar.
5.  **Verify:** Check the "Preview" tab for a JSON object with player names and hole scores.
6.  **Save:** Right-click the request -> **Copy** -> **Copy Response**. Paste into a new file `squabbit_raw.json`.
7.  **Resume:** Tell Gemini "I have the json" to proceed with parsing.

This document outlines the end-to-end workflow for updating the SG@SG website dashboards, from tournament data entry to live deployment.

## 1. Data Collection and Preparation (Automated)

### From Squabbit to Google Sheets (via LLM/Atlas)

1.  **Open Master Template:** Open the "SG-SG Data Template" in Google Sheets.
2.  **Run Prompts:** Use the prompts defined in `SOP_SG-SG.md` to extract data from Squabbit.
    *   *Tip:* Use **aText Macros** (detailed below) to quickly paste these prompts.
3.  **Data Extraction:** Populate the `RawScores`, `NetMedal`, `BB` (or `Quota`), `GrossSkins`, and `NetSkins` tabs.
    *   *Note:* Ensure unplayed team games (BB vs Quota) are left blank but the tabs remain.
4.  **Verification:** Briefly check that player names (e.g., "Miki") and money values are correct.

### Export to Excel

1.  **Download Command:** In Google Sheets, go to **File > Download > Microsoft Excel (.xlsx)**.
2.  **Naming Convention:** Save the file using the format: `YYYY-MM-DD_SG-SG_Data.xlsx` (e.g., `2025-12-20_SG-SG_Data.xlsx`).
3.  **Save Location:** Save this file directly into the project root folder: `~/Developer/Personal_Projects/website-sg-sg/`.

## 2. Executing the Automation Script
... (rest of the file remains valid) ...

### Running the Pipeline

1.  **Open Terminal**: Launch the Terminal app on your Mac.
2.  **Navigate to Project**:
    ```bash
    cd ~/Developer/Personal_Projects/website-sg-sg
    ```
3.  **Run Script**:
    ```bash
    python3 update_site.py
    ```

### What the Script (`update_site.py`) Does

The script executes a multi-stage data pipeline to ensure dashboard accuracy:

*   **Data Normalization**: Strips hidden spaces from player names and standardizes date formats to ensure matches across all sheets.
*   **Automated Write-up**: Generates a human-readable HTML summary of the latest tournament's results (e.g., winners, earnings) for the home page.
*   **Earnings Consolidation**: Aggregates money from Net Medal, Best Ball, Quota, and Skins into a single "Total Earnings" field per player.
*   **Seasonal Logic**: Filters data into the 2025 or 2026 seasons based on the tournament date (November start).
*   **Statistical Calculation**: Merges the `SG-SG_Data - Scorecard.csv` with raw scores to calculate hole averages and relative-to-par statistics.
*   **Handicap Audit**: Performs a "Dual Analysis" (Best 3 vs. Best 6 rounds) to flag potential handicap adjustments for the committee.

## 3. Dashboard Updates and HTML Injection

The script does not overwrite your HTML files; it performs a surgical "injection" of data into specific JavaScript variables.

*   **`index.html`**: Injects a full HTML block to replace the content of the "Latest Results" section with a tournament summary.
*   **`MoneyList2025/2026.html`**: Updates the `const csvData` variable with the new seasonal standings.
*   **`PlayerStats.html`**: Updates the `const playerStatsData` for individual performance cards.
*   **`AverageScore.html`**: Injects `const holeData` as a JSON array to update the circular gauges.
*   **`HoleIndex.html`**: Updates the scatter plot using `const rawData`.
*   **`HandicapAnalysis.html`**: Injects the committee review data into `dataBest3` and `dataBest6`.

## 4. Commitment and Deployment

### GitHub Sync

Once the HTML files are updated locally, the script automatically triggers Git commands:

1.  `git add .`: Stages all changes, including the new Excel data and updated HTML.
2.  `git commit -m "..."`: Saves the changes with a timestamped message.
3.  `git push`: Sends the updates to your repository at `github.com/CJROYCE4311/website-sg-sg`.

### Netlify Deployment

Your Netlify account is linked to your GitHub repository via "Continuous Deployment."

*   **Trigger**: As soon as the script completes the `git push`, Netlify detects the new commit.
*   **Build**: Netlify automatically rebuilds the site using the updated HTML files.
*   **Live**: The changes become live on your public URL within seconds of the Terminal showing "🎉 Done!".

## Troubleshooting Tips

*   **Blank Money List**: Ensure player names are spelled identically in both the RawScores and Earnings sheets.
*   **NaN Errors**: Verify that `SG-SG_Data - Scorecard.csv` is present in the folder and contains numeric values for Par and Hole.
*   **Deployment Lag**: If the site doesn't update, perform a Hard Refresh in your browser (**Cmd + Shift + R**) to bypass cached data.

## 5. Productivity Shortcuts (aText Macros)

### **✅ Completed**
| Abbreviation | Category | Purpose |
| :--- | :--- | :--- |
| `;sgpy` | Terminal | Navigate & Run Update Pipeline |
| `;sgge` | Terminal | Open Gemini CLI in project folder |
| `/team` | LLM | Prompt 1: Team Games |
| `/raw` | LLM | Prompt 2: Raw Scores |

### **⏳ To Be Done**
| Abbreviation | Category | Purpose |
| :--- | :--- | :--- |
| `/sgp3` | LLM | Prompt 3: Net Medal |
| `/sgp4` | LLM | Prompt 4: Skins |
| `;sggit` | Terminal | Git status & Diff check |
