import pandas as pd
import os
import json
import re
import subprocess
from datetime import datetime
import warnings

warnings.filterwarnings("ignore")

# --- CONFIGURATION ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
WEBSITE_DIR = os.path.join(PROJECT_ROOT, "website")

# CSV Paths
SCORES_FILE = os.path.join(DATA_DIR, "scores.csv")
FINANCIALS_FILE = os.path.join(DATA_DIR, "financials.csv")
HANDICAPS_FILE = os.path.join(DATA_DIR, "handicaps.csv")
COURSE_FILE = os.path.join(DATA_DIR, "course_info.csv")

# Constants
COURSE_RATING, SLOPE_RATING = 70.5, 124
MONTHS_LOOKBACK = 13

def inject_to_html(filename, var_name, content, is_json=False):
    """Replaces data variables in HTML files."""
    filepath = os.path.join(WEBSITE_DIR, filename)
    if not os.path.exists(filepath): 
        print(f"⚠️ Warning: {filename} not found.")
        return
        
    with open(filepath, 'r') as f: html = f.read()

    if is_json:
        replacement = f"const {var_name} = {json.dumps(content, indent=4)};"
        pattern = rf"const {var_name}\s*=\s*\[.*?\];"
    else:
        replacement = f"const {var_name} = `{content.strip()}`";
        pattern = rf"const {var_name}\s*=\s*[`].*?[`];"
    
    new_html = re.sub(pattern, replacement, html, flags=re.DOTALL)
    with open(filepath, 'w') as f: f.write(new_html)
    print(f"✅ Updated {filename}")

def get_latest_results_writeup(financials_df):
    """Generates the 'BOO-YAH' writeup from the latest date in financials."""
    if financials_df.empty: return ""
    
    # 1. Find latest date
    latest_date = financials_df['Date'].max()
    day_df = financials_df[financials_df['Date'] == latest_date].copy()
    
    date_str = latest_date.strftime('%Y-%m-%d')
    
    html = f"""
    <div class="mb-4 space-y-1">
        <h4 class="font-bold text-gray-900 text-lg m-0">BOO-YAH!</h4>
        <p class="text-sm m-0">Results for {date_str}.</p>
    </div>
    <div class="grid md:grid-cols-2 gap-x-8 gap-y-4 text-sm">
        <div class="space-y-4">
    """
    
    # Left Col: Team Games (Quota, BestBall, NetMedal)
    # Note: The CSV structure flattened everything into 'Category'.
    # We'll try to reconstruct the groupings.
    
    # Order: BestBall -> Quota -> NetMedal
    cat_map = {'BestBall': 'Best Ball', 'Quota': 'Team Quota', 'NetMedal': 'Net Medal'}
    
    for cat_key, cat_title in cat_map.items():
        cat_df = day_df[day_df['Category'] == cat_key]
        if not cat_df.empty:
            html += f"<div><h5 class='font-bold text-gray-900 mb-1 mt-0'>{cat_title}</h5><ul class='list-none pl-0 m-0 space-y-1'>"
            # Group by Amount to find teams/ties
            # Since we lost 'Team ID' in the flatten (unless we add it back), we group by amount implies a team or tie
            # This is a slight approximation but works for 95% of cases
            for amount, group in cat_df.groupby('Amount'):
                names = " & ".join(sorted(group['Player'].tolist()))
                html += f"<li class='m-0'>{names} - ${amount:.0f}</li>"
            html += "</ul></div>"

    html += "</div><div class='space-y-4'>" # Split Cols
    
    # Right Col: Skins
    for cat_key, cat_title in [('GrossSkins', 'Gross Skins'), ('NetSkins', 'Net Skins')]:
        cat_df = day_df[day_df['Category'] == cat_key]
        if not cat_df.empty:
            html += f"<div><h5 class='font-bold text-gray-900 mb-1 mt-0'>{cat_title}</h5><ul class='list-none pl-0 m-0 space-y-1'>"
            for _, row in cat_df.sort_values('Amount', ascending=False).iterrows():
                html += f"<li class='m-0'>{row['Player']} - ${row['Amount']:.0f}</li>"
            html += "</ul></div>"
            
    html += "</div></div>"
    html += f"<p class='text-xs text-gray-400 mt-6 mb-0 italic'>Run Date: {datetime.now().strftime('%Y-%m-%d')}</p>"
    return html

def update_index_html(writeup_html):
    filepath = os.path.join(WEBSITE_DIR, 'index.html')
    if not os.path.exists(filepath): return
    with open(filepath, 'r') as f: html = f.read()

    # Regex replace the prose div content
    pattern = r'(<div class="prose prose-green max-w-none text-gray-600 space-y-4">).*?(<p class=\'text-xs text-gray-400 mt-6 mb-0 italic\'>Run Date: .*?</p>)'
    if re.search(pattern, html, flags=re.DOTALL):
        html = re.sub(pattern, r'\1' + writeup_html, html, flags=re.DOTALL)
    
    with open(filepath, 'w') as f: f.write(html)
    print("✅ Updated index.html")

def run_pipeline():
    print("--- ⛳ Starting CSV-Based Site Refresh ---")
    
    # 1. Load Data
    if not os.path.exists(SCORES_FILE):
        print("❌ Critical: scores.csv not found.")
        return

    scores = pd.read_csv(SCORES_FILE, parse_dates=['Date'])
    financials = pd.read_csv(FINANCIALS_FILE, parse_dates=['Date']) if os.path.exists(FINANCIALS_FILE) else pd.DataFrame()
    course = pd.read_csv(COURSE_FILE) if os.path.exists(COURSE_FILE) else pd.DataFrame()
    
    # Normalize Course Info
    if not course.empty:
        course.columns = [c.strip().lower() for c in course.columns]
        course['hole'] = pd.to_numeric(course['hole'].astype(str).str.replace('H', ''), errors='coerce')
    
    # Filter 13 Months for Handicap Analysis
    cutoff_date = datetime.now() - pd.DateOffset(months=MONTHS_LOOKBACK)
    recent_scores = scores[scores['Date'] >= cutoff_date].copy()
    
    # 2. Prepare Base Dataframe (Scores + Financials Aggregated)
    # We need a master 'base' for the money lists and player stats
    # Group financials by Date/Player
    fin_agg = pd.DataFrame()
    if not financials.empty:
        fin_pivot = financials.pivot_table(index=['Date', 'Player'], columns='Category', values='Amount', aggfunc='sum').reset_index().fillna(0)
        # Rename columns to match legacy expectations
        col_map = {
            'BestBall': 'BB_Earn', 'Quota': 'Quota_Earn', 
            'NetMedal': 'net_medal_earnings', 
            'GrossSkins': 'Gskins_earnings', 'NetSkins': 'Nskins_earnings'
        }
        fin_pivot = fin_pivot.rename(columns=col_map)
        fin_agg = fin_pivot
    
    # Merge Scores with Financials
    # Note: scores has H1..H18, Gross_Score, Round_Handicap
    base = scores.copy()
    if not fin_agg.empty:
        base = base.merge(fin_agg, on=['Date', 'Player'], how='left')
    
    # Fill missing money with 0
    money_cols = ['BB_Earn', 'Quota_Earn', 'net_medal_earnings', 'Gskins_earnings', 'Nskins_earnings']
    for c in money_cols:
        if c not in base.columns: base[c] = 0.0
    base = base.fillna(0)
    base['Total_Earnings'] = base[money_cols].sum(axis=1)
    
    base['Tournament_Year'] = base['Date'].apply(lambda x: x.year + 1 if x.month >= 11 else x.year)

    # 3. Handicap Analysis (Best 3/6)
    # Calculate differentials
    base['Differential'] = (base['Gross_Score'] - COURSE_RATING) * 113 / SLOPE_RATING
    base['Differential'] = base['Differential'].round(1)
    
    analysis_data_best3 = []
    analysis_data_best6 = []

    # Use recent_scores for the analysis to respect the lookback, 
    # BUT we need to make sure we have the diffs calculated. 
    # Let's just use 'base' but filter inside the loop or pre-filter.
    # Actually, the requirement was "13 month lookback".
    
    analysis_base = base[base['Date'] >= cutoff_date].copy()

    for player, group in analysis_base.groupby('Player'):
        rounds = len(group)
        if rounds < 1: continue

        # Latest Handicap
        latest_row = group.sort_values('Date', ascending=False).iloc[0]
        # Prefer Round_Handicap from scores.csv
        current_hcp = float(latest_row['Round_Handicap']) if 'Round_Handicap' in latest_row else 0.0
        
        diffs = group['Differential'].dropna().tolist()
        gross_scores = group['Gross_Score'].tolist()
        
        avg_gross = sum(gross_scores) / len(gross_scores)
        avg_net = avg_gross - current_hcp

        # Best 3
        best3_diffs = sorted(diffs)[:3]
        implied_3 = sum(best3_diffs) / len(best3_diffs) if best3_diffs else 0
        adj_3 = implied_3 - current_hcp

        # Best 6
        best6_diffs = sorted(diffs)[:6]
        implied_6 = sum(best6_diffs) / len(best6_diffs) if best6_diffs else 0
        adj_6 = implied_6 - current_hcp

        common = {
            'name': player, 'current': round(current_hcp, 1),
            'avgGross': round(avg_gross, 1), 'avgNet': round(avg_net, 1),
            'rounds': rounds, 'notes': ''
        }
        analysis_data_best3.append({**common, 'implied': round(implied_3, 1), 'adjustment': round(adj_3, 1)})
        analysis_data_best6.append({**common, 'implied': round(implied_6, 1), 'adjustment': round(adj_6, 1)})
    
    inject_to_html("HandicapAnalysis.html", "dataBest3", analysis_data_best3, is_json=True)
    inject_to_html("HandicapAnalysis.html", "dataBest6", analysis_data_best6, is_json=True)

    # 4. Handicap Detail (Drilldown)
    detail_lines = ["Player\tDate\tGross Score\tHCP Used\tNet Score\tRound Differential\tTotal_Rounds_Available\tNotes"]
    rounds_map = base.groupby('Player').size().to_dict()
    
    # Sort entire history for detail view
    for _, row in base.sort_values(['Player', 'Date'], ascending=[True, False]).iterrows():
        d_str = row['Date'].strftime('%Y-%m-%d')
        hcp = row.get('Round_Handicap', 0.0)
        gross = row['Gross_Score']
        net = gross - hcp
        diff = row['Differential']
        r_count = rounds_map.get(row['Player'], 0)
        detail_lines.append(f"{row['Player']}\t{d_str}\t{gross}\t{hcp:.1f}\t{net:.1f}\t{diff:.1f}\t{r_count}\t")
    
    detail_path = os.path.join(WEBSITE_DIR, "Handicap_Detail.html")
    if os.path.exists(detail_path):
        with open(detail_path, 'r') as f: html = f.read()
        new_content = "\n".join(detail_lines)
        pattern = r'(<script id="rawData" type="text/plain">)(.*?)(</script>)'
        new_html = re.sub(pattern, r'\1\n' + new_content + r'\n\3', html, flags=re.DOTALL)
        with open(detail_path, 'w') as f: f.write(new_html)
        print("✅ Updated Handicap_Detail.html")

    # 5. Money Lists
    for year in [2025, 2026]:
        df_year = base[base['Tournament_Year'] == year].groupby('Player')[money_cols + ['Total_Earnings']].sum().reset_index()
        df_year = df_year.sort_values('Total_Earnings', ascending=False)
        
        # Rename for JS
        cols_out = ['Player', 'BB_Earn', 'Quota_Earn', 'Nskins_earnings', 'Gskins_earnings', 'net_medal_earnings', 'Total_Earnings']
        headers = ['Name', 'Best_Ball_Earnings', 'Quota_Earnings', 'Net_Skins_Earnings', 'Gross_Skins_Earnings', 'Net_Earnings', 'Total Earnings']
        
        # 2025 didn't have Quota? Legacy script checked year. 
        # We'll just output all columns, the JS handles 0s fine usually, or we match legacy.
        if year == 2025:
             # Legacy excluded Quota for 2025
             df_out = df_year[['Player', 'BB_Earn', 'Nskins_earnings', 'Gskins_earnings', 'net_medal_earnings', 'Total_Earnings']]
             df_out.columns = ['Name', 'Best_Ball_Earnings', 'Net_Skins_Earnings', 'Gross_Skins_Earnings', 'Net_Earnings', 'Total Earnings']
        else:
             df_out = df_year[cols_out]
             df_out.columns = headers
             
        inject_to_html(f"MoneyList{year}.html", "csvData", df_out.to_csv(index=False))

    # 6. Hole Averages
    score_cols = [f'H{i}' for i in range(1, 19)]
    # Use ALL scores for averages, not just recent? Legacy used 'raw' which was all loaded files.
    melted = scores.melt(id_vars=['Player', 'Date'], value_vars=score_cols, var_name='hole', value_name='score')
    melted['hole'] = pd.to_numeric(melted['hole'].str.replace('H', ''), errors='coerce')
    
    hole_avg = melted.groupby('hole')['score'].mean().round(2).reset_index()
    if not course.empty:
        hole_avg = hole_avg.merge(course[['hole', 'par']], on='hole', how='left')
    hole_avg['par'] = hole_avg['par'].fillna(4).astype(int)
    
    inject_to_html("AverageScore.html", "holeData", hole_avg[['hole', 'score', 'par']].to_dict('records'), is_json=True)

    # 7. Hole Index (Calculated)
    sg_index_map = {1: 5, 2: 15, 3: 13, 4: 7, 5: 1, 6: 17, 7: 9, 8: 3, 9: 11, 
                    10: 12, 11: 14, 12: 2, 13: 16, 14: 10, 15: 6, 16: 18, 17: 8, 18: 4}
    
    idx_df = hole_avg.copy()
    idx_df['diff'] = idx_df['score'] - idx_df['par']
    idx_df = idx_df.sort_values('diff', ascending=False)
    idx_df['rank'] = range(1, 19)
    
    hole_index_data = [{"hole": int(r['hole']), "x": sg_index_map.get(r['hole'], 0), "y": int(r['rank'])} for _, r in idx_df.iterrows()]
    inject_to_html("HoleIndex.html", "rawData", hole_index_data, is_json=True)

    # 8. Player Stats
    # All time stats
    stats_df = base.copy()
    stats_df['Net_Score'] = stats_df['Gross_Score'] - stats_df['Round_Handicap']
    stats_df['Net_to_Par'] = stats_df['Net_Score'] - 72
    
    p_stats = stats_df.groupby('Player').agg({
        'Gross_Score': 'mean', 'Net_Score': 'mean', 'Net_to_Par': 'mean'
    }).round(2).reset_index()
    p_stats.columns = ['Player', 'Gross_Score', 'net_score', 'Net_to_Par']
    inject_to_html("PlayerStats.html", "playerStatsData", p_stats.to_csv(index=False))

    # 9. Latest Results Writeup
    writeup = get_latest_results_writeup(financials)
    if writeup:
        update_index_html(writeup)

def sync():
    print("🚀 Pushing Updates...")
    subprocess.run(["git", "add", "."], cwd=PROJECT_ROOT)
    subprocess.run(["git", "commit", "-m", f"Automated Update {datetime.now().strftime('%Y-%m-%d')}"], cwd=PROJECT_ROOT)
    subprocess.run(["git", "push"], cwd=PROJECT_ROOT)
    print("🎉 Done.")

if __name__ == "__main__":
    run_pipeline()
    sync()