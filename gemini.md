# Standard Operating Procedure (SOP): SG@SG Dashboard Update Process

This document outlines the end-to-end workflow for updating the SG@SG website dashboards, from tournament data entry to live deployment.

## 1. Data Collection and Preparation

### From Squabbit.com to Apple Numbers

1.  **Export Data**: Log in to Squabbit.com and download the tournament results for the current period.
2.  **Update Master File**: Open your master Apple Numbers file located in `~/Developer/Personal_Projects/website-sg-sg/`.
3.  **Input Data**: Copy the tournament data into the respective sheets:
    *   **RawScores**: Date, Name, and hole-by-hole scores.
    *   **NetMedal**: Placement and earnings.
    *   **BB / Quota**: Team earnings or quota points.
    *   **Skins**: Both Gross and Net skin counts and earnings.
    *   **Handicaps**: Updated Handicap Index (HI) and Course Handicap for the day.

### Export to Excel

1.  **Export Command**: In Apple Numbers, go to **File > Export To > Excel...**.
2.  **Naming Convention**: Save the file using the format: `YYYY-MM-DD_SG-SG_Data.xlsx` (e.g., `2025-12-20_SG-SG_Data.xlsx`).
3.  **Save Location**: Save this file directly into the project root folder: `~/Developer/Personal_Projects/website-sg-sg/`.

## 2. Executing the Automation Script

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
*   **Earnings Consolidation**: Aggregates money from Net Medal, Best Ball, Quota, and Skins into a single "Total Earnings" field per player.
*   **Seasonal Logic**: Filters data into the 2025 or 2026 seasons based on the tournament date (November start).
*   **Statistical Calculation**: Merges the `SG-SG_Data - Scorecard.csv` with raw scores to calculate hole averages and relative-to-par statistics.
*   **Handicap Audit**: Performs a "Dual Analysis" (Best 3 vs. Best 6 rounds) to flag potential handicap adjustments for the committee.

## 3. Dashboard Updates and HTML Injection

The script does not overwrite your HTML files; it performs a surgical "injection" of data into specific JavaScript variables.

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
