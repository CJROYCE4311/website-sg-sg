import pandas as pd
import glob
import os
import json
import re
import subprocess
from datetime import datetime

# --- CONFIGURATION ---
BASE_PATH = os.path.expanduser("~/Developer/Personal_Projects/website-sg-sg")
SCORECARD_FILE = os.path.join(BASE_PATH, "SG-SG_Data - Scorecard.csv")
COURSE_RATING, SLOPE_RATING, PAR_BASELINE = 70.5, 124, 72
MONTHS_LOOKBACK = 13

import warnings
warnings.filterwarnings("ignore")

def clean_player_data(df):
    """Normalizes names and dates for consistent merging."""
    if df.empty: return df
    df.columns = [c.strip() for c in df.columns]
    p_col = next((c for c in df.columns if c.lower() in ['player', 'name']), None)
    if p_col:
        df = df.rename(columns={p_col: 'Player'})
        df['Player'] = df['Player'].astype(str).str.strip().str.title()
    d_col = next((c for c in df.columns if c.lower() == 'date'), None)
    if d_col:
        df[d_col] = pd.to_datetime(df[d_col], errors='coerce').dt.normalize()
        df = df.rename(columns={d_col: 'date'})
    return df

def to_numeric_safe(df, columns):
    """Forces columns to numbers, treating errors as 0."""
    for col in columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace('$', '').str.replace(',', '').str.strip(), errors='coerce').fillna(0.0)
    return df

def inject_to_html(filename, var_name, content, is_json=False):
    """Replaces data variables in HTML files while preserving existing code."""
    filepath = os.path.join(BASE_PATH, filename)
    if not os.path.exists(filepath): return
    with open(filepath, 'r') as f: html = f.read()

    # --- DATA INJECTION ---
    if is_json:
        replacement = f"const {var_name} = {json.dumps(content, indent=4)};"
        pattern = rf"const {var_name}\s*=\s*\[.*?\];"
    else:
        replacement = f"const {var_name} = `{content.strip()}`;"
        pattern = rf"const {var_name}\s*=\s*[`].*?[`];"
    
    new_html = re.sub(pattern, replacement, html, flags=re.DOTALL)
    with open(filepath, 'w') as f: f.write(new_html)
    print(f"✅ Updated {filename}")

def generate_writeup_html(file_path):
    """Generates an HTML writeup from the latest tournament data."""
    try:
        xls = pd.read_excel(file_path, sheet_name=None)
        
        writeup = "<h4>BOO-YAH!</h4><p>Welcome back to the SG@SG post-game wrap-up, where the only thing cooler than the winter air is the ice in our players' veins. Let's get right to the action!</p>"

        # Quota Game (Team)
        if 'Quota' in xls:
            quota_df = xls['Quota'].copy()
            quota_df['Player'] = quota_df['Player'].astype(str).str.strip().str.title()
            
            teams = {}
            for placement, group in quota_df.groupby('Placement'):
                players = group['Player'].tolist()
                earnings = group['Team_earnings'].sum()
                
                team_name = " & ".join(players)
                if team_name not in teams:
                    teams[team_name] = {'Placement': placement, 'Earnings': earnings}

            sorted_teams = sorted(teams.items(), key=lambda item: item[1]['Placement'])

            if sorted_teams:
                writeup += "<h5>Team Quota Game</h5><p>Things were tighter than a new pair of golf shoes!</p><ul>"
                
                for team_name, data in sorted_teams:
                    if data['Earnings'] > 0:
                        writeup += f"<li><strong>{data['Placement']}(st/nd/rd) Place:</strong> {team_name} - ${data['Earnings']:.2f}</li>"
                writeup += "</ul>"


        # Net Medal (Individual)
        if 'NetMedal' in xls:
            net_medal_df = xls['NetMedal'].copy()
            net_medal_df['Player'] = net_medal_df['Player'].astype(str).str.strip().str.title()
            
            writeup += "<h5>Individual Net Medal</h5><p>Players were going mano a mano!</p><ul>"
            
            for placement, group in net_medal_df.groupby('Placement'):
                if group['net_medal_earnings'].sum() > 0:
                    names = ", ".join(group['Player'].tolist())
                    earnings = group['net_medal_earnings'].sum()
                    writeup += f"<li><strong>{placement}(st/nd/rd) Place:</strong> {names} - ${earnings:.2f}</li>"
            writeup += "</ul>"


        # Skins
        skins_writeup = ""
        for skin_type in ['GrossSkins', 'NetSkins']:
            if skin_type in xls:
                skins_df = xls[skin_type].copy()
                if not skins_df.empty:
                    skins_df['Player'] = skins_df['Player'].astype(str).str.strip().str.title()
                    earnings_col = 'Gskins_earnings' if skin_type == 'GrossSkins' else 'Nskins_earnings'
                    if earnings_col in skins_df.columns:
                        skins_summary = skins_df.groupby('Player')[earnings_col].sum().sort_values(ascending=False)
                        if not skins_summary.empty:
                            skins_writeup += f"<h5>{skin_type}</h5><ul>"
                            for i in range(len(skins_summary)):
                                if skins_summary.iloc[i] > 0:
                                    skins_writeup += f"<li>{skins_summary.index[i]} - ${skins_summary.iloc[i]:.2f}</li>"
                            skins_writeup += "</ul>"
        
        if skins_writeup:
            writeup += "<h5>Skins Game</h5>" + skins_writeup

        writeup += "<p>That's all the time we have! Until next time, Holla!</p>"
        
        return writeup

    except Exception as e:
        print(f"An error occurred during writeup generation: {e}")
        return ""

def update_index_html(writeup_html):
    """Updates the index.html file with the latest results writeup."""
    filepath = os.path.join(BASE_PATH, 'index.html')
    if not os.path.exists(filepath): return

    with open(filepath, 'r') as f:
        html = f.read()

    # Replace title
    html = re.sub(r'<h2 class="text-2xl font-bold text-gray-900">.*</h2>', 
                  r'<h2 class="text-2xl font-bold text-gray-900">Latest Results</h2>', html)

    # Replace content
    html = re.sub(r'(<div class="prose prose-green max-w-none text-gray-600 space-y-4">).*(</div>)',
                  r'\1' + writeup_html + r'\2', html, flags=re.DOTALL)

    with open(filepath, 'w') as f:
        f.write(html)
    print("✅ Updated index.html with the latest writeup.")

def run_pipeline():
    print("--- ⛳ Starting Site Refresh ---")
    excel_files = glob.glob(os.path.join(BASE_PATH, "2*.xlsx"))
    
    # Find the latest excel file
    latest_file = max(excel_files, key=os.path.getctime) if excel_files else None

    # 1. Load Scorecard
    scorecard = pd.read_csv(SCORECARD_FILE) if os.path.exists(SCORECARD_FILE) else pd.DataFrame()
    if not scorecard.empty:
        scorecard.columns = [c.strip().lower() for c in scorecard.columns]
        h_col = next((c for c in scorecard.columns if 'hole' in c), 'hole')
        p_col = next((c for c in scorecard.columns if 'par' in c), 'par')
        scorecard = scorecard.rename(columns={h_col: 'hole', p_col: 'par'})
        scorecard['hole'] = pd.to_numeric(scorecard['hole'].astype(str).str.replace('H', ''), errors='coerce')
        scorecard = scorecard[['hole', 'par']].dropna()

    # 2. Load All Data
    dfs = {k: [] for k in ['RawScores', 'NetMedal', 'BB', 'Team', 'Quota', 'GrossSkins', 'NetSkins']}
    for f in excel_files:
        xls = pd.read_excel(f, sheet_name=None)
        for key in dfs.keys():
            if key in xls: dfs[key].append(clean_player_data(xls[key]))
    master = {k: pd.concat(v, ignore_index=True) if v else pd.DataFrame() for k, v in dfs.items()}

    # 3. Consolidate
    raw = master['RawScores'].copy()
    raw = to_numeric_safe(raw, ['Gross_Score'] + [f'H{i}' for i in range(1, 19)])
    raw['Tournament_Year'] = raw['date'].apply(lambda x: x.year + 1 if x.month >= 11 else x.year)

    # Earnings logic
    net_medal = to_numeric_safe(master['NetMedal'].copy(), ['net_medal_earnings'])
    gross_skins = to_numeric_safe(master['GrossSkins'].copy(), ['Gskins_earnings'])
    net_skins = to_numeric_safe(master['NetSkins'].copy(), ['Nskins_earnings'])
    bb_df = to_numeric_safe(pd.concat([master['Team'].rename(columns={'Team_earnings': 'BB_Earn'}), 
                                      master['BB'].rename(columns={'BB_earnings': 'BB_Earn'})], ignore_index=True), ['BB_Earn'])
    quota_df = to_numeric_safe(master['Quota'].copy(), ['Team_earnings', 'Quota_earnings'])
    quota_df['Quota_Earn'] = quota_df.filter(regex='earnings|Earn').sum(axis=1)

    # Merge
    base = raw.rename(columns={'Gross_Score': 'Gross_Score'})
    for df_to_merge, col_name in [(net_medal, 'net_medal_earnings'), (bb_df, 'BB_Earn'), 
                                 (quota_df, 'Quota_Earn'), (gross_skins, 'Gskins_earnings'), (net_skins, 'Nskins_earnings')]:
        if not df_to_merge.empty:
            df_agg = df_to_merge.groupby(['date', 'Player'])[col_name].sum().reset_index()
            base = base.merge(df_agg, on=['date', 'Player'], how='left')
    
    money_cols = ['net_medal_earnings', 'BB_Earn', 'Quota_Earn', 'Gskins_earnings', 'Nskins_earnings']
    for col in money_cols:
        if col not in base.columns: base[col] = 0.0
    base = base.fillna(0)
    base['Total_Earnings'] = base[money_cols].sum(axis=1)

    # 4. Injections
    # Money Lists
    for year in [2025, 2026]:
        df_year = base[base['Tournament_Year'] == year].groupby('Player').agg({
            'BB_Earn': 'sum', 'Quota_Earn': 'sum', 'Nskins_earnings': 'sum', 'Gskins_earnings': 'sum', 'net_medal_earnings': 'sum', 'Total_Earnings': 'sum'
        }).reset_index().sort_values('Total_Earnings', ascending=False)
        
        if year == 2025:
            df_out = df_year[['Player', 'BB_Earn', 'Nskins_earnings', 'Gskins_earnings', 'net_medal_earnings', 'Total_Earnings']]
            df_out.columns = ['Name', 'Best_Ball_Earnings', 'Net_Skins_Earnings', 'Gross_Skins_Earnings', 'Net_Earnings', 'Total Earnings']
        else:
            df_out = df_year[['Player', 'BB_Earn', 'Quota_Earn', 'Nskins_earnings', 'Gskins_earnings', 'net_medal_earnings', 'Total_Earnings']]
            df_out.columns = ['Name', 'Best_Ball_Earnings', 'Quota_Earnings', 'Net_Skins_Earnings', 'Gross_Skins_Earnings', 'Net_Earnings', 'Total Earnings']
        
        inject_to_html(f"MoneyList{year}.html", "csvData", df_out.to_csv(index=False))

    # Hole Averages (Standardized to lowercase 'par' for gauge rendering)
    melted = raw.melt(id_vars=['Player', 'date'], value_vars=[f'H{i}' for i in range(1, 19)], var_name='hole', value_name='score')
    melted['hole'] = pd.to_numeric(melted['hole'].str.replace('H', ''), errors='coerce')
    hole_avg = melted.groupby('hole')['score'].mean().round(2).reset_index()
    if not scorecard.empty:
        hole_avg = hole_avg.merge(scorecard, on='hole', how='left')
    hole_avg['par'] = hole_avg['par'].fillna(4).astype(int)
    inject_to_html("AverageScore.html", "holeData", hole_avg[['hole', 'score', 'par']].to_dict('records'), is_json=True)
    
    # Generate and inject writeup
    if latest_file:
        writeup = generate_writeup_html(latest_file)
        if writeup:
            update_index_html(writeup)

def sync():
    print("🚀 Pushing Updates...")
    subprocess.run(["git", "add", "."], cwd=BASE_PATH)
    subprocess.run(["git", "commit", "-m", "Final Master Sync: Corrected casing and removed redundant healing logic"], cwd=BASE_PATH)
    subprocess.run(["git", "push"], cwd=BASE_PATH)
    print("🎉 Done! All 7 dashboards are corrected and live.")

if __name__ == "__main__":
    run_pipeline()
    sync()