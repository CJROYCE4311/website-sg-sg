# Standard Operating Procedure (SOP): SG@SG Dashboard Update Process

## 1. Project Structure

The project is organized to separate data, code, and content:

*   **`data/`**: Source of Truth. Contains the CSV databases:
    *   `scores.csv`: Player scores, score differentials, partners, and rankings.
    *   `financials.csv`: Winnings and payouts. This file may contain payout-only rows when screenshots are preserved but scores later disappear in Squabbit.
    *   `handicaps.csv`: Historical handicap snapshots with handicap index and course handicap.
    *   `player_aliases.json`: Known player-name aliases that should normalize to canonical names.
*   **`website/`**: Contains the live HTML site (`index.html`, `PlayerStats.html`, etc.).
    *   `website/data/methodology_data.json` and `website/data/methodology_data.js` are generated from the canonical CSVs during site refresh.
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

### Step 2: Agent Execution (Codex)
Instruct Codex to process the screenshots in stages and keep the output local to this directory.

The Agent will perform the following "Conductor" Track:

1.  **Staged Extraction:** Read the screenshots in `input/screenshots/` in batches.
2.  **Data Extraction:** Extract:
    *   Scores and handicap indexes (converting `+` to negative numbers).
    *   Course handicaps should be derived from the handicap snapshot formula, not copied into `scores.csv`.
    *   **Financials:** Payout amounts per category.
    *   If a best-ball screenshot also shows handicap indexes, use it as a handicap source only for players who also appear in the scored field for that date.
    *   **Meta Data:** Partners, Team Ranks, and Individual Ranks.
3.  **Review Gate:** Consolidate the reviewed output into `input/tournament_data.json`.
    *   Start from `docs/tournament_data.template.json` so the payload shape stays consistent.
    *   Include a `metadata` block whenever possible:
        *   `full_scorecard_available: true/false`
        *   `handicap_list_available: true/false`
        *   `screenshots: []`
        *   `source_notes: []`
        *   `approximations: []`
    *   Keep handicap data in `handicaps[]`, not in `scores[]`.
4.  **Validation:** Run:
    ```bash
    python3 scripts/process_tournament.py input/tournament_data.json --dry-run
    ```
    Then run the canonical audit if you want a clean checklist before write:
    ```bash
    python3 scripts/audit_canonical_data.py --json-file input/tournament_data.json
    ```
5.  **Ingestion:** After validation, run:
    ```bash
    python3 scripts/process_tournament.py input/tournament_data.json
    ```
    *   *Note:* Scores are upserted, corrected handicaps update existing date/player rows, corrected financials update existing date/player/category rows, player aliases are normalized before validation, and the ingest aborts before writing if duplicate canonical keys are detected, if scored players are missing same-date handicap snapshots, or if handicap snapshots exist for players who do not have a score row for that date.
    *   *Financial exception:* payout-only financial rows are allowed when they come from preserved payout screenshots, even if Squabbit later loses the score rows.
    *   *Exception path:* `--allow-incomplete` exists for intentional partial events, but use it only when the JSON metadata clearly documents why the event is incomplete.
6.  **Site Generation:** The ingestion script automatically triggers a local `update_site.py` build.
    *   This rebuild also refreshes the methodology data bundle under `website/data/`.
7.  **Cleanup:** Move used screenshots to `input/processed/YYYY-MM-DD/`.
8.  **Deployment:** Publish only from an explicit deployment step, not from routine local processing.
    *   *Guardrail:* Publish stages only `data/` and `website/`, and aborts if unrelated repo files are dirty.

### Step 3: Verification (User)
*   **Homepage:** Check "Latest Results" for correct Team/Net placements (e.g., "1: Scott Lucas").
*   **Player Stats:** Verify the "Player Metrics" gauge visuals.
*   **Analysis:** Verify the "Handicap Analysis" page shows the new round.

## 3. Script Logic (`update_site.py`)

*   **Source:** Reads directly from `data/*.csv`.
*   **Calculations:**
    *   **Differentials:** `(Gross - 70.5) * 113 / 124`
    *   **Course Handicap:** `Handicap Index * (124 / 113) + (70.5 - 72)`
    *   **Gap:** `Differential - Course Handicap` (Negative = Beat Course Handicap).
*   **Writeups:**
    *   **Merged Data:** Combines Financials with Score data to display Rankings and Partners in the results feed.
    *   **Format:** Lists one team/player per line for readability.
*   **Deployment:** Local builds do not commit or push unless `--publish` is explicitly used.

## 4. Troubleshooting

*   **Duplicate Names:** If names appear twice (e.g., "Steve McCormick" vs "Steve Mccormick"), ask the Agent to run a normalization step to fix capitalization and merge records.
*   **Alias Hygiene:** Update `data/player_aliases.json` when a new nickname, casing variant, or OCR misspelling shows up more than once.
*   **Missing Ranks:** If placements are missing in the recap, provide the Agent with the specific rankings to "Upsert" into the database.
*   **"Blank" Analysis Page:** Ensure the `Handicaps` column in CSV is populated.
*   **Visual Glitches:** If gauges look wrong, ensure `PlayerStats.html` has the latest JS logic for the 3-segment color arc.
