import pandas as pd
import glob
import os
import json
import re
import subprocess
from datetime import timedelta

# --- CONFIGURATION ---
BASE_PATH = os.path.expanduser("~/Developer/Personal_Projects/website-sg-sg")
SCORECARD_FILE = os.path.join(BASE_PATH, "SG-SG_Data - Scorecard.csv")
MONTHS_LOOKBACK = 13
COURSE_RATING, SLOPE_RATING, PAR = 70.5, 124, 72

def inject_to_html(filename, variable_name, new_content, is_json=False, is_script_tag=False):
    """Replaces hardcoded data in stand-alone HTML files."""
    filepath = os.path.join(BASE_PATH, filename)
    if not os.path.exists(filepath): return
    with open(filepath, 'r') as f: content = f.read()

    if is_script_tag: # For Handicap_Detail.html
        pattern = rf'(<script id="{variable_name}" type="text/plain">).*?(</script>)'
        replacement = rf'\1\nPlayer\tDate\tGross Score\tHCP Used\tNet Score\tRound Differential\tTotal_Rounds_Available\tNotes\n{new_content}\2'
    elif is_json:
        replacement = f"const {variable_name} = {json.dumps(new_content, indent=4)};"
        pattern = rf"const {variable_name}\s*=\s*\[.*?\];"
    else:
        replacement = f"const {variable_name} = `{new_content.strip()}`;"
        pattern = rf"const {variable_name}\s*=\s*[`].*?[`];"

    new_html = re.sub(pattern, replacement, content, flags=re.DOTALL)
    with open(filepath, 'w') as f: f.write(new_html)
    print(f"✅ Updated {filename}")

def run_automation():
    print("--- ⛳ Starting Site Update ---")
    
    # 1. LOAD ALL DATA
    excel_files = glob.glob(os.path.join(BASE_PATH, "*.xlsx"))
    scorecard = pd.read_csv(SCORECARD_FILE) if os.path.exists(SCORECARD_FILE) else pd.DataFrame()
    
    dfs = {'RawScores': [], 'NetMedal': [], 'BB': [], 'Team': [], 'Quota': [], 'GrossSkins': [], 'NetSkins': [], 'Handicaps': []}
    for f in excel_files:
        xls = pd.read_excel(f, sheet_name=None)
        for key in dfs.keys():
            if key in xls: dfs[key].append(xls[key])
    
    # Consolidate sheets
    master = {k: pd.concat(v, ignore_index=True) if v else pd.DataFrame() for k, v in dfs.items()}
    
    # 2. PROCESS MONEY & STATS (Script 1 Logic)
    # [Internal Data Cleaning/Merging Logic here...]
    # (Abbreviated for clarity: this generates money_df, player_stats_df, hole_stats)
    
    # 3. HANDICAP ANALYSIS (Script 2 Logic)
    # (Uses logic from your second script to generate df_summary_3, df_summary_6, and df_details)
    
    # 4. INJECT INTO HTML
    # Money List
    inject_to_html("MoneyList2025.html", "csvData", master['NetMedal'].to_csv(index=False)) # Example
    
    # Player Stats
    # inject_to_html("PlayerStats.html", "playerStatsData", player_stats_df.to_csv(index=False))
    
    # Hole Stats
    # inject_to_html("AverageScore.html", "holeData", hole_js_data, is_json=True)
    # inject_to_html("HoleIndex.html", "rawData", index_js_data, is_json=True)
    
    # Handicap Dashboard
    # inject_to_html("HandicapAnalysis.html", "dataBest3", df_summary_3.to_dict('records'), is_json=True)
    # inject_to_html("HandicapAnalysis.html", "dataBest6", df_summary_6.to_dict('records'), is_json=True)
    # inject_to_html("Handicap_Detail.html", "rawData", df_details.to_csv(index=False, sep='\t', header=False), is_script_tag=True)

def sync_github():
    print("🚀 Pushing to GitHub...")
    try:
        os.chdir(BASE_PATH)
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", "Automated Site Update"], check=True)
        subprocess.run(["git", "push"], check=True)
        print("🎉 Site is live!")
    except Exception as e: print(f"❌ Git Push Failed: {e}")

if __name__ == "__main__":
    run_automation()
    sync_github()