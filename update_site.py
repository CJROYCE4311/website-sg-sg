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
    for col in columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace('$', '').str.replace(',', '').str.strip(), errors='coerce').fillna(0.0)
    return df

def inject_to_html(filename, var_name, content, is_json=False):
    filepath = os.path.join(BASE_PATH, filename)
    if not os.path.exists(filepath): return
    with open(filepath, 'r') as f: html = f.read()
    if is_json:
        replacement = f"const {var_name} = {json.dumps(content, indent=4)};"
        pattern = rf"const {var_name}\s*=\s*\[.*?\];"
    else:
        replacement = f"const {var_name} = `{content.strip()}`;"
        pattern = rf"const {var_name}\s*=\s*[`].*?[`];"
    new_html = re.sub(pattern, replacement, html, flags=re.DOTALL)
    with open(filepath, 'w') as f: f.write(new_html)
    print(f"✅ Updated {filename}")

def run_pipeline():
    print("--- ⛳ Starting Site Refresh ---")
    excel_files = glob.glob(os.path.join(BASE_PATH, "*.xlsx"))
    print(f"Found {len(excel_files)} data files.")
    
    # Load Scorecard
    scorecard = pd.read_csv(SCORECARD_FILE) if os.path.exists(SCORECARD_FILE) else pd.DataFrame()
    if not scorecard.empty:
        scorecard.columns = [c.strip() for c in scorecard.columns]
        h_col = next((c for c in scorecard.columns if 'hole' in c.lower()), 'Hole')
        p_col = next((c for c in scorecard.columns if 'par' in c.lower()), 'Par')
        scorecard = scorecard.rename(columns={h_col: 'Hole', p_col: 'Par'})
        scorecard['Hole'] = pd.to_numeric(scorecard['Hole'].astype(str).str.replace('H', ''), errors='coerce')
        scorecard = scorecard[['Hole', 'Par']].dropna()

    # Load All Tournament Data
    dfs = {k: [] for k in ['RawScores', 'NetMedal', 'BB', 'Team', 'Quota', 'GrossSkins', 'NetSkins']}
    for f in excel_files:
        xls = pd.read_excel(f, sheet_name=None)
        for key in dfs.keys():
            if key in xls: dfs[key].append(clean_player_data(xls[key]))
    master = {k: pd.concat(v, ignore_index=True) if v else pd.DataFrame() for k, v in dfs.items()}

    # Aggregate Scores & Earnings
    raw = master['RawScores'].copy()
    raw = to_numeric_safe(raw, ['Gross_Score'] + [f'H{i}' for i in range(1, 19)])
    raw['Tournament_Year'] = raw['date'].apply(lambda x: x.year + 1 if x.month >= 11 else x.year)

    print(f"Total Rounds found: {len(raw)}")
    print(f"2025 Rounds: {len(raw[raw.Tournament_Year == 2025])}")
    print(f"2026 Rounds: {len(raw[raw.Tournament_Year == 2026])}")

    # Process Money
    net_medal = to_numeric_safe(master['NetMedal'].copy(), ['net_medal_earnings'])
    gross_skins = to_numeric_safe(master['GrossSkins'].copy(), ['Gskins_earnings'])
    net_skins = to_numeric_safe(master['NetSkins'].copy(), ['Nskins_earnings'])
    bb_df = to_numeric_safe(pd.concat([master['Team'].rename(columns={'Team_earnings': 'BB_Earn'}), 
                                      master['BB'].rename(columns={'BB_earnings': 'BB_Earn'})], ignore_index=True), ['BB_Earn'])
    quota_df = master['Quota'].copy()
    q_cols = [c for c in ['Team_earnings', 'Quota_earnings', 'Quota_Earn'] if c in quota_df.columns]
    quota_df = to_numeric_safe(quota_df, q_cols)
    quota_df['Quota_Earn'] = quota_df[q_cols].sum(axis=1) if q_cols else 0.0

    # Master Merge
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

    # 1. Update Money Lists (FIXING HEADERS)
    for year in [2025, 2026]:
        df_year = base[base['Tournament_Year'] == year].groupby('Player').agg({
            'BB_Earn': 'sum', 'Quota_Earn': 'sum', 'Nskins_earnings': 'sum', 'Gskins_earnings': 'sum', 'net_medal_earnings': 'sum', 'Total_Earnings': 'sum'
        }).reset_index().sort_values('Total_Earnings', ascending=False)
        
        # Mapping columns to match exact HTML Variable Requirements
        if year == 2025:
            df_out = df_year[['Player', 'BB_Earn', 'Nskins_earnings', 'Gskins_earnings', 'net_medal_earnings', 'Total_Earnings']]
            df_out.columns = ['Name', 'Best_Ball_Earnings', 'Net_Skins_Earnings', 'Gross_Skins_Earnings', 'Net_Earnings', 'Total Earnings']
        else:
            df_out = df_year[['Player', 'BB_Earn', 'Quota_Earn', 'Nskins_earnings', 'Gskins_earnings', 'net_medal_earnings', 'Total_Earnings']]
            df_out.columns = ['Name', 'Best_Ball_Earnings', 'Quota_Earnings', 'Net_Skins_Earnings', 'Gross_Skins_Earnings', 'Net_Earnings', 'Total Earnings']
        
        inject_to_html(f"MoneyList{year}.html", "csvData", df_out.to_csv(index=False))

    # 2. Update Average Score (FIXING NaN)
    melted = raw.melt(id_vars=['Player', 'date'], value_vars=[f'H{i}' for i in range(1, 19)], var_name='hole', value_name='score')
    melted['hole'] = pd.to_numeric(melted['hole'].str.replace('H', ''), errors='coerce')
    hole_avg = melted.groupby('hole')['score'].mean().round(2).reset_index()
    
    if not scorecard.empty:
        hole_avg['hole'] = hole_avg['hole'].astype(int)
        scorecard['Hole'] = scorecard['Hole'].astype(int)
        hole_avg = hole_avg.merge(scorecard, left_on='hole', right_on='Hole', how='left')
    
    # Force par to 4 if missing to prevent NaN
    hole_avg['Par'] = hole_avg['Par'].fillna(4).astype(int)
    inject_to_html("AverageScore.html", "holeData", hole_avg[['hole', 'score', 'Par']].to_dict('records'), is_json=True)

def sync():
    print("🚀 Pushing to GitHub...")
    subprocess.run(["git", "add", "."], cwd=BASE_PATH)
    subprocess.run(["git", "commit", "-m", "Final Fix: Corrected Header mapping and NaN Par mapping"], cwd=BASE_PATH)
    subprocess.run(["git", "push"], cwd=BASE_PATH)
    print("🎉 Dashboards are now fully populated!")

if __name__ == "__main__":
    run_pipeline()
    sync()