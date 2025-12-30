# SOP: Manual Tournament Data Entry (TSV Copy-Paste)

> **☀️ MORNING CHECKLIST:**
> 1. **Modify Template:** Ensure Google Sheet `Quota` and `BB` tabs have `Team_ID` in Column B.
> 2. **Test Dec 20 Data:** Run the Prompts below against the Dec 20 Squabbit results.
> 3. **Verify Write-up:** Run the python script and confirm tied teams are separated correctly in `index.html`.

**Objective:** Use an LLM to extract data from Squabbit results...

---

## **Step 1: The Prompts**
Navigate to the specific results page on Squabbit for each game, then use the corresponding prompt below.

### **Prompt 1: Team Games (Quota or Best Ball)**
> "IMMEDIATELY analyze the active browser tab to extract team results from the SG@SG tournament page. Take over the current Squabbit leaderboard page and compile all team results into a TSV. Scroll through the entire list from top to bottom so every team is captured. For each team, output a row per player with columns: Date (YYYY-MM-DD), Team_ID (assigned in page order), Player, Placement (remove ‘T’ if present), Net_Total from the ‘TOT’ column (treat ‘E’ as 0), and Earnings as a plain number without the dollar sign. Include all players even if their earnings are zero. Omit the header row."

### **Prompt 2: Raw Scores (Hole-by-Hole)**
> "IMMEDIATELY analyze the active browser tab to extract the full hole-by-hole leaderboard from the SG@SG tournament page. Take over the current Squabbit page and compile all results into a TSV. Scroll through the entire list from top to bottom so every player is captured. For each player, output a row with columns: Date (YYYY-MM-DD), Name (copy EXACTLY as shown), H1, H2, H3, H4, H5, H6, H7, H8, H9, H10, H11, H12, H13, H14, H15, H16, H17, H18, and Gross_Score. Ensure every hole contains a numeric value. Omit the header row."

### **Prompt 3: Net Medal**
> "Access the Net leaderboard. Compile into TSV format with these columns: date, Player, Placement, net_tot, net_medal_earnings. Drop the 'T' from placement. Omit header row."

### **Prompt 4: Skins (Gross & Net)**
> "Access the Skins results. Compile into TSV format with these columns: date, Player, Skins_count, Skins_earnings. Create two separate TSV blocks: one for Gross Skins and one for Net Skins. Omit header rows."

---

## **Step 2: Google Sheet Layout (Column Check)**
Ensure your Google Sheet tabs match these columns exactly before pasting:

| Tab | Col A | Col B | Col C | Col D | Col E | ... |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **RawScores** | Date | Name | H1 | H2 | ... | Gross_Score (Col U) |
| **Handicaps** | Date | Player | HI | Course_Handicap | | |
| **NetMedal** | date | Player | Placement | net_tot | net_medal_earnings | | 
| **Quota** | date | Team_ID | Player | Placement | Team_net | Team_earnings |
| **BB** | date | Team_ID | Player | Placement | Team_net | Team_earnings |
| **GrossSkins**| date | Player | Gskins_count| Gskins_earnings| | |
| **NetSkins** | date | Player | Nskins_count| Nskins_earnings| | |

---

## **Step 3: Finalization**
1.  **Paste:** Paste the TSV data into the corresponding Google Sheet tabs.
2.  **Download:** **File > Download > Microsoft Excel (.xlsx)**.
3.  **Rename:** `YYYY-MM-DD_SG-SG_Data.xlsx`.
3.  **Run Pipeline:** 
    ```bash
    python3 update_site.py
    ```

---

## **aText Macros (Shortcuts)**
Use these abbreviations in **aText** to instantly paste long prompts or commands. 
*Naming Logic:* `/` for LLM Prompts, `;` for Terminal Commands, `.` for General Text.

### **✅ Completed Shortcuts**
| Abbreviation | Purpose | Expanded Text / Command |
| :--- | :--- | :--- |
| `;sgpy` | **Terminal** | `cd ~/Developer/Personal_Projects/website-sg-sg && python3 update_site.py` |
| `;sgge` | **Terminal** | `sggem` (Opens Gemini CLI in project folder) |
| `/team` | **LLM Prompt** | Team Games (Quota/Best Ball) extraction. |
| `/raw` | **LLM Prompt** | Raw Scores (Hole-by-Hole) extraction. |

### **⏳ To Be Done (Pending Verification)**
| Abbreviation | Purpose | Status |
| :--- | :--- | :--- |
| `/sgp3` | Net Medal Prompt | Pending Atlas Test |
| `/sgp4` | Skins Prompt | Pending Atlas Test |
| `;sggit` | Git Check Command | Pending Verification |
