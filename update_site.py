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
COURSE_RATING, SLOPE_RATING, PAR = 70.5, 124, 72
MONTHS_LOOKBACK = 13

import warnings
warnings.filterwarnings("ignore")

def clean_data(df):
    """Normalizes names and dates for consistent merging."""
    if df.empty: return df
    # Normalize Player Names (Strip spaces and Title Case)
    p_col = next((c for c in df.columns if c.lower() in ['player', 'name']), None)
    if p_col:
        df = df.rename(columns={p_col: 'Player'})
        df['Player'] = df['Player'].astype(str).str.strip().str.title()
    
    # Normalize Dates to pure date objects
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

def inject_to_html(filename, var_name, content, is_json=False, is_detail_tag=False):
    filepath = os.path.join(BASE_PATH, filename)
    if not os.path.exists(filepath): return
    with open(filepath, 'r') as f: html = f.read()

    if is_detail_tag: # For Handicap_Detail.html tab-separated data
        pattern = rf'(<script id="{var_name}" type="text/plain">).*?(</script>)'
        replacement = rf'\1\nPlayer\tDate\tGross Score\tHCP Used\tNet Score\tRound Differential\tTotal_Rounds_Available\tNotes\n{content}\2'
    elif is_json:
        replacement = f"const {var_name} = {json.dumps(content, indent=4)};"
        pattern = rf"const {var_name}\s*=\s*\[.*?\];"
    else:
        replacement = f"const {var_name} = `{content.strip()}`;"
        pattern = rf"const {var_name}\s*=\s*[`].*?[`];"

    new_html = re.sub(pattern, replacement, html, flags=re.DOTALL)
    with open(filepath, 'w') as f: f.write(new_html)
    print(f"✅ Updated {filename}")

def run_pipeline():
    print("--- ⛳ Starting Full Site Pipeline ---")
    
    # 1. LOAD & CLEAN ALL EXCEL FILES
    excel_files = glob.glob(os.path.join(BASE_PATH, "*.xlsx"))
    scorecard = pd.read_csv(SCORECARD_FILE) if os.path.exists(SCORECARD_FILE) else pd.DataFrame()
    if not scorecard.empty:
        scorecard['Hole'] = pd.to_numeric(scorecard['Hole'].astype(str).str.replace('H', ''), errors='coerce')

    dfs = {k: [] for k in ['RawScores', 'NetMedal', 'BB', 'Team', 'Quota', 'GrossSkins', 'NetSkins', 'Handicaps']}
    for f in excel_files:
        xls = pd.read_excel(f, sheet_name=None)
        for key in dfs.keys():
            if key in xls: dfs[key].append(clean_data(xls[key]))

    master = {k: pd.concat(v, ignore_index=True) if v else pd.DataFrame() for k, v in dfs.items()}

    # 2. CONSOLIDATE TOURNAMENT DATA
    raw = master['RawScores'].copy()
    if raw.empty: return print("❌ No RawScores found.")
    
    raw = to_numeric_safe(raw, ['Gross_Score'] + [f'H{i}' for i in range(1, 19)])
    raw['Tournament_Year'] = raw['date'].apply(lambda x: x.year + 1 if x.month >= 11 else x.year)

    # Aggregating Earnings
    net_medal = to_numeric_safe(master['NetMedal'].copy(), ['net_medal_earnings'])
    gross_skins = to_numeric_safe(master['GrossSkins'].copy(), ['Gskins_earnings'])
    net_skins = to_numeric_safe(master['NetSkins'].copy(), ['Nskins_earnings'])
    bb_df = to_numeric_safe(pd.concat([master['Team'].rename(columns={'Team_earnings': 'BB_Earn'}), 
                                      master['BB'].rename(columns={'BB_earnings': 'BB_Earn'})], ignore_index=True), ['BB_Earn'])
    quota_df = to_numeric_safe(master['Quota'].copy(), ['Team_earnings']).rename(columns={'Team_earnings': 'Quota_Earn'})

    # Master Merge for Money & Stats
    base = raw.rename(columns={'Gross_Score': 'Gross_Score'})
    for df_to_merge in [net_medal, bb_df, quota_df, gross_skins, net_skins]:
        if not df_to_merge.empty:
            cols = [c for c in ['date', 'Player', 'net_medal_earnings', 'BB_Earn', 'Quota_Earn', 'Gskins_earnings', 'Nskins_earnings'] if c in df_to_merge.columns]
            df_agg = df_to_merge.groupby(['date', 'Player'])[cols[2:]].sum().reset_index()
            base = base.merge(df_agg, on=['date', 'Player'], how='left')
    
    base = base.fillna(0)
    base['Total_Earnings'] = base[['net_medal_earnings', 'BB_Earn', 'Quota_Earn', 'Gskins_earnings', 'Nskins_earnings']].sum(axis=1)

    # 3. UPDATE ALL DASHBOARDS
    # A. Money Lists
    for year in [2025, 2026]:
        df_year = base[base['Tournament_Year'] == year].groupby('Player').agg({
            'BB_Earn': 'sum', 'Nskins_earnings': 'sum', 'Gskins_earnings': 'sum', 'net_medal_earnings': 'sum', 'Total_Earnings': 'sum'
        }).reset_index().sort_values('Total_Earnings', ascending=False)
        df_year.columns = ['Name', 'Best_Ball_Earnings', 'Net_Skins_Earnings', 'Gross_Skins_Earnings', 'Net_Earnings', 'Total Earnings']
        inject_to_html(f"MoneyList{year}.html", "csvData", df_year.to_csv(index=False))

    # B. Player Stats & Handicap Audit
    hcp_master = to_numeric_safe(master['Handicaps'].copy(), ['Course_Handicap', 'HI'])
    base = base.merge(hcp_master[['date', 'Player', 'HI', 'Course_Handicap']], on=['date', 'Player'], how='left').fillna(0)
    base['net_score'] = base['Gross_Score'] - base['Course_Handicap']
    base['Differential'] = ((base['Gross_Score'] - COURSE_RATING) * (113 / SLOPE_RATING)).round(1)

    p_stats = base.groupby('Player').agg({'Gross_Score': 'mean', 'net_score': 'mean'}).reset_index().round(2)
    p_stats['Net_to_Par'] = (p_stats['net_score'] - PAR).round(2)
    inject_to_html("PlayerStats.html", "playerStatsData", p_stats[['Player', 'Gross_Score', 'net_score', 'Net_to_Par']].to_csv(index=False))

    # C. Hole Data (AverageScore.html & HoleIndex.html)
    melted = raw.melt(id_vars=['Player', 'date'], value_vars=[f'H{i}' for i in range(1, 19)], var_name='hole', value_name='score')
    melted['hole'] = pd.to_numeric(melted['hole'].str.replace('H', ''), errors='coerce')
    hole_avg = melted.groupby('hole')['score'].mean().round(2).reset_index().merge(scorecard, left_on='hole', right_on='Hole', how='left')
    
    inject_to_html("AverageScore.html", "holeData", hole_avg[['hole', 'score', 'Par']].to_dict('records'), is_json=True)
    
    # Fix for HoleIndex Scatter Plot
    hole_avg['SG-SG_Handicap'] = hole_avg['score'].rank(ascending=False).astype(int)
    index_data = []
    for _, row in hole_avg.iterrows():
        index_data.append({
            "hole": int(row['hole']),
            "x": int(row['HI']) if 'HI' in row else 0,
            "y": int(row['SG-SG_Handicap'])
        })
    inject_to_html("HoleIndex.html", "rawData", index_data, is_json=True)

    # D. Handicap Audit
    cutoff = base['date'].max() - pd.DateOffset(months=MONTHS_LOOKBACK)
    recent = base[base['date'] >= cutoff].copy()
    def get_audit(df, n):
        res = []
        for p, g in df.groupby('Player'):
            top = g.sort_values(['net_score', 'date'], ascending=[True, False]).head(n)
            hi = g.sort_values('date', ascending=False).iloc[0]['HI']
            implied = round(top['Differential'].mean(), 1)
            res.append({"name": p, "implied": implied, "current": round(hi, 1), "adjustment": round(min(0, implied-hi), 1),
                        "avgGross": round(top['Gross_Score'].mean(), 1), "avgNet": round(top['net_score'].mean(), 1), 
                        "rounds": len(g), "notes": ""})
        return res

    inject_to_html("HandicapAnalysis.html", "dataBest3", get_audit(recent, 3), is_json=True)
    inject_to_html("HandicapAnalysis.html", "dataBest6", get_audit(recent, 6), is_json=True)
    
    # Handicap Detail Table (Fixes the AttributeError)
    detail_rows = base.sort_values(['Player', 'date'], ascending=[True, False])
    detail_txt = ""
    for r in detail_rows.itertuples(index=False):
        # Accessing by name is safer than by index _3
        rounds_count = len(base[base.Player == r.Player])
        detail_txt += f"{r.Player}\t{r.date.strftime('%Y-%m-%d')}\t{r.Gross_Score}\t{r.Course_Handicap}\t{r.net_score}\t{r.Differential}\t{rounds_count}\t\n"
    inject_to_html("Handicap_Detail.html", "rawData", detail_txt, is_detail_tag=True)

def sync():
    print("🚀 Pushing Updates...")
    subprocess.run(["git", "add", "."], cwd=BASE_PATH)
    subprocess.run(["git", "commit", "-m", "Final Bug Fix: Handicap Detail Table and Money Lists"], cwd=BASE_PATH)
    subprocess.run(["git", "push"], cwd=BASE_PATH)
    print("🎉 All 7 Dashboards Updated and Live!")

if __name__ == "__main__":
    run_pipeline()
    sync()