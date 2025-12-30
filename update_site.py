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
        
        # Header
        writeup = """
        <div class="mb-4 space-y-1">
            <h4 class="font-bold text-gray-900 text-lg m-0">BOO-YAH!</h4>
            <p class="text-sm m-0">Another classic SG@SG saturday in the books. Here is the lowdown.</p>
        </div>
        
        <div class="grid md:grid-cols-2 gap-x-8 gap-y-4 text-sm">
            <div class="space-y-4">
        """

        # LEFT COLUMN: Team Games (Quota or Best Ball) & Net Medal
        # Team Game Logic (Handles both Quota and BB)
        team_game_html = ""
        for sheet_name, title in [('Quota', 'Team Quota'), ('BB', 'Best Ball')]:
            if sheet_name in xls and not xls[sheet_name].empty:
                df = xls[sheet_name].copy()
                earnings_col = 'Team_earnings' if 'Team_earnings' in df.columns else 'BB_earnings'
                df = to_numeric_safe(df, [earnings_col])
                df['Player'] = df['Player'].astype(str).str.strip().str.title()
                
                teams = {}
                # Determine grouping: Use Team_ID if present to separate tied teams
                group_cols = ['Placement']
                if 'Team_ID' in df.columns:
                    group_cols.append('Team_ID')

                for keys, group in df.groupby(group_cols):
                    # Unpack placement (it's the first key)
                    placement = keys[0] if isinstance(keys, tuple) else keys
                    
                    players = group['Player'].tolist()
                    earnings = group[earnings_col].iloc[0] # Take first row's earnings (assumed per-team total) or sum if per-player
                    # If earnings in sheet are per-player, sum them. If per-team, take one. 
                    # Convention: Usually input as Total Team Earnings per row. 
                    # If duplicate rows per player have same total, don't sum. 
                    # SAFEST: Sum and divide by player count? No.
                    # LET'S ASSUME: Sheet contains "Team Earnings" repeated for each player.
                    # So we take the max (or mean) of the group.
                    earnings = group[earnings_col].max() 

                    team_name = " & ".join(players)
                    unique_key = f"{placement}_{team_name}" # ensure uniqueness in dict
                    teams[unique_key] = {'Placement': placement, 'Earnings': earnings, 'Names': team_name}

                sorted_teams = sorted(teams.values(), key=lambda x: str(x['Placement']))

                if sorted_teams:
                    team_game_html += f"<div><h5 class='font-bold text-gray-900 mb-1 mt-0'>{title}</h5><ul class='list-none pl-0 m-0 space-y-1'>"
                    for data in sorted_teams:
                        if data['Earnings'] > 0:
                            team_game_html += f"<li class='m-0'><span class='font-semibold'>{data['Placement']} Place:</span> {data['Names']} - ${data['Earnings']:.0f}</li>"
                    team_game_html += "</ul></div>"
        
        writeup += team_game_html

        # Net Medal
        if 'NetMedal' in xls:
            net_medal_df = xls['NetMedal'].copy()
            net_medal_df = to_numeric_safe(net_medal_df, ['net_medal_earnings'])
            net_medal_df['Player'] = net_medal_df['Player'].astype(str).str.strip().str.title()
            
            writeup += "<div><h5 class='font-bold text-gray-900 mb-1 mt-0'>Net Medal</h5><ul class='list-none pl-0 m-0 space-y-1'>"
            valid_entries = False
            for placement, group in net_medal_df.groupby('Placement'):
                if group['net_medal_earnings'].sum() > 0:
                    valid_entries = True
                    names = ", ".join(group['Player'].tolist())
                    earnings = group['net_medal_earnings'].sum()
                    writeup += f"<li class='m-0'><span class='font-semibold'>{placement} Place:</span> {names} - ${earnings:.0f}</li>"
            writeup += "</ul></div>"

        writeup += "</div><div class='space-y-4'>" # End Left Col, Start Right Col

        # RIGHT COLUMN: Skins
        skins_html = ""
        for skin_type in ['GrossSkins', 'NetSkins']:
            if skin_type in xls:
                skins_df = xls[skin_type].copy()
                earnings_col = 'Gskins_earnings' if skin_type == 'GrossSkins' else 'Nskins_earnings'
                skins_df = to_numeric_safe(skins_df, [earnings_col])
                
                if not skins_df.empty:
                    skins_df['Player'] = skins_df['Player'].astype(str).str.strip().str.title()
                    if earnings_col in skins_df.columns:
                        totals = skins_df.groupby('Player')[earnings_col].sum().sort_values(ascending=False)
                        totals = totals[totals > 0]
                        
                        if not totals.empty:
                            title = "Gross Skins" if skin_type == 'GrossSkins' else "Net Skins"
                            skins_html += f"<div><h5 class='font-bold text-gray-900 mb-1 mt-0'>{title}</h5><ul class='list-none pl-0 m-0 space-y-1'>"
                            for player, amount in totals.items():
                                skins_html += f"<li class='m-0'>{player} - ${amount:.2f}</li>"
                            skins_html += "</ul></div>"
        
        writeup += skins_html
        writeup += "</div></div>" # End Right Col, End Grid

        writeup += "<p class='text-xs text-gray-400 mt-6 mb-0 italic'>Run Date: " + datetime.now().strftime('%Y-%m-%d') + "</p>"
        
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
    html = re.sub(r'<h2 class="text-2xl font-bold text-gray-900">Welcome to the 2026 Season</h2>', 
                  r'<h2 class="text-2xl font-bold text-gray-900">Latest Results</h2>', html)

    # Replace content with a non-greedy match targeting the prose div inside the announcements id
    # Note: We now look for the prose div relative to "Latest Results" header if identifiers shifted,
    # but based on the manual edit, the structure is still a div with id="announcements" > div > div with class="prose..."
    # Simpler regex to just find the prose div following "Latest Results"
    
    # Locate the "Latest Results" h2, then find the next prose div
    # Or just target the specific prose class if unique enough. It is unique "prose-green".
    
    html = re.sub(r'(<div class="prose prose-green max-w-none text-gray-600 space-y-4">).*?(</div>\s*</div>)',
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
    dfs = {k: [] for k in ['RawScores', 'NetMedal', 'BB', 'Team', 'Quota', 'GrossSkins', 'NetSkins', 'Handicaps']}
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
    
    # Handle BB earnings column naming (Team_earnings vs BB_earnings)
    bb_data = master['BB'].copy()
    if 'Team_earnings' in bb_data.columns:
        bb_data = bb_data.rename(columns={'Team_earnings': 'BB_Earn'})
    if 'BB_earnings' in bb_data.columns:
        bb_data = bb_data.rename(columns={'BB_earnings': 'BB_Earn'})

    bb_df = to_numeric_safe(pd.concat([master['Team'].rename(columns={'Team_earnings': 'BB_Earn'}), 
                                      bb_data], ignore_index=True), ['BB_Earn'])
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

    # --- HANDICAP ANALYSIS ---
    handicaps = master['Handicaps'].copy() if 'Handicaps' in master else pd.DataFrame()
    if not handicaps.empty:
        handicaps = to_numeric_safe(handicaps, ['Handicap'])
        if 'date' in handicaps.columns:
            base = base.merge(handicaps[['date', 'Player', 'Handicap']], on=['date', 'Player'], how='left')
        else:
            base = base.merge(handicaps[['Player', 'Handicap']], on=['Player'], how='left')
    
    score_cols = [f'H{i}' for i in range(1, 19)]
    if 'Gross_Score' not in base.columns:
         base['Gross_Score'] = base[score_cols].sum(axis=1)
    else:
         mask = base['Gross_Score'] == 0
         base.loc[mask, 'Gross_Score'] = base.loc[mask, score_cols].sum(axis=1)

    base['Differential'] = (base['Gross_Score'] - COURSE_RATING) * 113 / SLOPE_RATING
    base['Differential'] = base['Differential'].round(1)

    analysis_data = []
    for player, group in base.groupby('Player'):
        diffs = group.sort_values('date', ascending=False)['Differential'].dropna().tolist()
        if len(diffs) >= 1:
            best3 = sum(sorted(diffs)[:3]) / min(len(diffs), 3)
            best6 = sum(sorted(diffs)[:6]) / min(len(diffs), 6)
            analysis_data.append({'name': player, 'best3': round(best3, 1), 'best6': round(best6, 1)})
            
    inject_to_html("HandicapAnalysis.html", "dataBest3", [{'x': d['name'], 'y': d['best3']} for d in analysis_data], is_json=True)
    inject_to_html("HandicapAnalysis.html", "dataBest6", [{'x': d['name'], 'y': d['best6']} for d in analysis_data], is_json=True)

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
    commit_message = f"Automated Site Update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    subprocess.run(["git", "commit", "-m", commit_message], cwd=BASE_PATH)
    subprocess.run(["git", "push"], cwd=BASE_PATH)
    print("🎉 Done! All dashboards are corrected and live.")

if __name__ == "__main__":
    run_pipeline()
    sync()