import pandas as pd
import glob
import os
import json
import re
import subprocess
from datetime import datetime
import warnings

warnings.filterwarnings("ignore")

# --- CONFIGURATION ---
# Determine paths relative to this script's location
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
WEBSITE_DIR = os.path.join(PROJECT_ROOT, "website")

SCORECARD_FILE = os.path.join(DATA_DIR, "SG-SG_Data - Scorecard.csv")
COURSE_RATING, SLOPE_RATING, PAR_BASELINE = 70.5, 124, 72
MONTHS_LOOKBACK = 13

def clean_player_data(df):
    """Normalizes names and dates for consistent merging."""
    if df.empty: return df
    df.columns = [c.strip() for c in df.columns]
    # Remove duplicate columns after stripping (keeps first occurrence)
    df = df.loc[:, ~df.columns.duplicated()]
    
    # Standardize Handicap
    if 'HI' in df.columns: df = df.rename(columns={'HI': 'Handicap'})
    if 'Handicap Index' in df.columns: df = df.rename(columns={'Handicap Index': 'Handicap'})

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
    filepath = os.path.join(WEBSITE_DIR, filename)
    if not os.path.exists(filepath): 
        print(f"⚠️ Warning: Could not find {filename} in {WEBSITE_DIR}")
        return
        
    with open(filepath, 'r') as f: html = f.read()

    # --- DATA INJECTION ---
    if is_json:
        replacement = f"const {var_name} = {json.dumps(content, indent=4)};"
        pattern = rf"const {var_name}\s*=\s*\[.*?\];"
    else:
        replacement = f"const {var_name} = `{content.strip()}`;";
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
                    # earnings = group[earnings_col].iloc[0] # Take first row's earnings (assumed per-team total) or sum if per-player
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
                    earnings = group['net_medal_earnings'].iloc[0]
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
    filepath = os.path.join(WEBSITE_DIR, 'index.html')
    if not os.path.exists(filepath): 
        print(f"⚠️ Warning: Could not find index.html in {WEBSITE_DIR}")
        return

    with open(filepath, 'r') as f:
        html = f.read()

    # Replace title
    html = re.sub(r'<h2 class="text-2xl font-bold text-gray-900">Welcome to the 2026 Season</h2>', 
                  r'<h2 class="text-2xl font-bold text-gray-900">Latest Results</h2>', html)

    # Replace content.
    pattern = r'(<div class="prose prose-green max-w-none text-gray-600 space-y-4">).*?(<p class=\'text-xs text-gray-400 mt-6 mb-0 italic\'>Run Date: .*?</p>)'
    
    if re.search(pattern, html, flags=re.DOTALL):
        html = re.sub(pattern, r'\1' + writeup_html, html, flags=re.DOTALL)
    else:
        # If pattern not found, try inserting inside the div if it exists
        if '<div class="prose prose-green max-w-none text-gray-600 space-y-4">' in html:
             print("ℹ️ Standard pattern not found. Attempting to insert content into prose div.")
             html = html.replace('<div class="prose prose-green max-w-none text-gray-600 space-y-4">', 
                                 '<div class="prose prose-green max-w-none text-gray-600 space-y-4">' + writeup_html)
        else:
             print("⚠️ Could not find the 'Latest Results' prose section in index.html.")

    with open(filepath, 'w') as f:
        f.write(html)
    print("✅ Updated index.html with the latest writeup.")

def run_pipeline():
    print("--- ⛳ Starting Site Refresh ---")
    print(f"📂 Project Root: {PROJECT_ROOT}")
    print(f"📂 Data Dir: {DATA_DIR}")
    
    all_excel_files = glob.glob(os.path.join(DATA_DIR, "2*.xlsx"))
    excel_files = []
    
    # Filter 13 Months
    cutoff_date = datetime.now() - pd.DateOffset(months=MONTHS_LOOKBACK)
    for f in all_excel_files:
        basename = os.path.basename(f)
        try:
            date_part = basename[:10]
            file_date = datetime.strptime(date_part, '%Y-%m-%d')
            if file_date >= cutoff_date:
                excel_files.append(f)
        except:
            excel_files.append(f) # Include if date parse fails
    
    # Find the latest excel file
    latest_file = max(excel_files, key=os.path.getctime) if excel_files else None
    if latest_file:
        print(f"📅 Latest Data File: {os.path.basename(latest_file)}")
    else:
        print("⚠️ No data files found!")

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
    if master['RawScores'].empty:
        print("⚠️ No Raw Scores found. Exiting.")
        return

    raw = master['RawScores'].copy()
    raw = to_numeric_safe(raw, ['Gross_Score'] + [f'H{i}' for i in range(1, 19)])
    raw['Tournament_Year'] = raw['date'].apply(lambda x: x.year + 1 if x.month >= 11 else x.year)

    # Earnings logic
    net_medal = to_numeric_safe(master['NetMedal'].copy(), ['net_medal_earnings'])
    gross_skins = to_numeric_safe(master['GrossSkins'].copy(), ['Gskins_earnings'])
    net_skins = to_numeric_safe(master['NetSkins'].copy(), ['Nskins_earnings'])
    
    # Handle BB earnings column naming (Team_earnings vs BB_earnings)
    bb_data = master['BB'].copy()
    
    # Coalesce Team_earnings and BB_earnings into BB_Earn
    cols = bb_data.columns
    if 'Team_earnings' in cols and 'BB_earnings' in cols:
        # Fill NaN with 0 before adding
        bb_data['BB_Earn'] = pd.to_numeric(bb_data['Team_earnings'], errors='coerce').fillna(0) + \
                             pd.to_numeric(bb_data['BB_earnings'], errors='coerce').fillna(0)
        bb_data = bb_data.drop(columns=['Team_earnings', 'BB_earnings'])
    elif 'Team_earnings' in cols:
        bb_data = bb_data.rename(columns={'Team_earnings': 'BB_Earn'})
    elif 'BB_earnings' in cols:
        bb_data = bb_data.rename(columns={'BB_earnings': 'BB_Earn'})
        
    # Remove any duplicate columns that might remain (e.g., duplicate dates/players)
    bb_data = bb_data.loc[:, ~bb_data.columns.duplicated()]

    team_data = master['Team'].copy()
    if 'Team_earnings' in team_data.columns:
        team_data = team_data.rename(columns={'Team_earnings': 'BB_Earn'})
    # Remove duplicates in team_data columns
    team_data = team_data.loc[:, ~team_data.columns.duplicated()]

    bb_df = to_numeric_safe(pd.concat([team_data, bb_data], ignore_index=True), ['BB_Earn'])
    
    quota_df = to_numeric_safe(master['Quota'].copy(), ['Team_earnings', 'Quota_earnings'])
    quota_df['Quota_Earn'] = quota_df.filter(regex='earnings|Earn').sum(axis=1)

    # Merge
    base = raw.rename(columns={'Gross_Score': 'Gross_Score'})
    for df_to_merge, col_name in [(net_medal, 'net_medal_earnings'), (bb_df, 'BB_Earn'), 
                                 (quota_df, 'Quota_Earn'), (gross_skins, 'Gskins_earnings'), (net_skins, 'Nskins_earnings')]:
        if not df_to_merge.empty:
            # Ensure date and Player are consistent for merge
            if 'date' in df_to_merge.columns and 'Player' in df_to_merge.columns:
                 # Group by key to avoid duplicates causing merge explosion (sum earnings if multiple entries)
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
        # Columns already normalized in clean_player_data
        # Remove duplicate columns (keep last) just in case
        handicaps = handicaps.loc[:, ~handicaps.columns.duplicated(keep='last')]

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

    analysis_data_best3 = []
    analysis_data_best6 = []

    for player, group in base.groupby('Player'):
        rounds = len(group)
        if rounds < 1: continue

        # Get latest handicap
        latest_row = group.sort_values('date', ascending=False).iloc[0]
        current_hcp = float(latest_row['Handicap']) if 'Handicap' in latest_row and pd.notnull(latest_row['Handicap']) else 0.0
        
        diffs = group['Differential'].dropna().tolist()
        gross_scores = group['Gross_Score'].tolist()
        
        avg_gross = sum(gross_scores) / len(gross_scores)
        avg_net = avg_gross - current_hcp 

        # Best 3 Logic
        best3_diffs = sorted(diffs)[:3]
        implied_3 = sum(best3_diffs) / len(best3_diffs) if best3_diffs else 0
        adj_3 = implied_3 - current_hcp

        # Best 6 Logic
        best6_diffs = sorted(diffs)[:6]
        implied_6 = sum(best6_diffs) / len(best6_diffs) if best6_diffs else 0
        adj_6 = implied_6 - current_hcp

        common_stats = {
            'name': player,
            'current': round(current_hcp, 1),
            'avgGross': round(avg_gross, 1),
            'avgNet': round(avg_net, 1),
            'rounds': rounds,
            'notes': '' 
        }

        analysis_data_best3.append({
            **common_stats,
            'implied': round(implied_3, 1),
            'adjustment': round(adj_3, 1)
        })

        analysis_data_best6.append({
            **common_stats,
            'implied': round(implied_6, 1),
            'adjustment': round(adj_6, 1)
        })
            
    inject_to_html("HandicapAnalysis.html", "dataBest3", analysis_data_best3, is_json=True)
    inject_to_html("HandicapAnalysis.html", "dataBest6", analysis_data_best6, is_json=True)

    # --- Handicap Detail Injection ---
    detail_lines = ["Player\tDate\tGross Score\tHCP Used\tNet Score\tRound Differential\tTotal_Rounds_Available\tNotes"]
    rounds_map = base.groupby('Player').size().to_dict()
    
    for _, row in base.sort_values(['Player', 'date'], ascending=[True, False]).iterrows():
        date_str = row['date'].strftime('%Y-%m-%d')
        hcp = float(row['Handicap']) if pd.notnull(row['Handicap']) else 0.0
        gross = int(row['Gross_Score']) if pd.notnull(row['Gross_Score']) else 0
        net = gross - hcp
        diff = float(row['Differential']) if pd.notnull(row['Differential']) else 0.0
        rounds = rounds_map.get(row['Player'], 0)
        
        line = f"{row['Player']}\t{date_str}\t{gross}\t{hcp:.1f}\t{net:.1f}\t{diff:.1f}\t{rounds}\t"
        detail_lines.append(line)
        
    detail_path = os.path.join(WEBSITE_DIR, "Handicap_Detail.html")
    if os.path.exists(detail_path):
        with open(detail_path, 'r') as f: html = f.read()
        new_content = "\n".join(detail_lines)
        pattern = r'(<script id="rawData" type="text/plain">)(.*?)(</script>)'
        new_html = re.sub(pattern, r'\1\n' + new_content + r'\n\3', html, flags=re.DOTALL)
        with open(detail_path, 'w') as f: f.write(new_html)
        print("✅ Updated Handicap_Detail.html with new data")

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

    # --- Hole Index Calculation (SG@SG vs Sterling Grove) ---
    # Standard Sterling Grove Indices (Hardcoded map)
    sg_index_map = {1: 5, 2: 15, 3: 13, 4: 7, 5: 1, 6: 17, 7: 9, 8: 3, 9: 11, 
                    10: 12, 11: 14, 12: 2, 13: 16, 14: 10, 15: 6, 16: 18, 17: 8, 18: 4}
    
    # Calculate SG@SG difficulty ranking
    # Difficulty = Average Score - Par
    hole_index_df = hole_avg.copy()
    hole_index_df['diff'] = hole_index_df['score'] - hole_index_df['par']
    # Rank descending (Higher diff = Harder = Rank 1)
    hole_index_df = hole_index_df.sort_values('diff', ascending=False)
    hole_index_df['rank'] = range(1, 19)
    
    # Construct JSON data for HoleIndex.html
    hole_index_data = []
    for _, row in hole_index_df.iterrows():
        h = int(row['hole'])
        hole_index_data.append({
            "hole": h,
            "x": sg_index_map.get(h, 0),
            "y": int(row['rank'])
        })
    # Inject into HoleIndex.html
    inject_to_html("HoleIndex.html", "rawData", hole_index_data, is_json=True)
    
    # --- Player Stats Injection ---
    # Calculate stats: Average Gross, Average Net, Average Net to Par
    if not base.empty:
        stats_df = base.copy()
        # Ensure Net Score exists (Gross - Handicap)
        stats_df['Net_Score'] = stats_df['Gross_Score'] - stats_df['Handicap']
        stats_df['Net_to_Par'] = stats_df['Net_Score'] - 72

        # Aggregate by Player
        player_stats = stats_df.groupby('Player').agg({
            'Gross_Score': 'mean',
            'Net_Score': 'mean',
            'Net_to_Par': 'mean'
        }).reset_index()

        player_stats = player_stats.round(2)
        
        # Rename columns to match JS expectations in PlayerStats.html: Player,Gross_Score,net_score,Net_to_Par
        player_stats.columns = ['Player', 'Gross_Score', 'net_score', 'Net_to_Par']
        
        inject_to_html("PlayerStats.html", "playerStatsData", player_stats.to_csv(index=False))

    # Generate and inject writeup
    if latest_file:
        writeup = generate_writeup_html(latest_file)
        if writeup:
            update_index_html(writeup)

def sync():
    print("🚀 Pushing Updates...")
    # Add everything in the project root
    subprocess.run(["git", "add", "."], cwd=PROJECT_ROOT)
    
    commit_message = f"Automated Site Update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    # Commit
    subprocess.run(["git", "commit", "-m", commit_message], cwd=PROJECT_ROOT)
    
    # Push
    subprocess.run(["git", "push"], cwd=PROJECT_ROOT)
    print("🎉 Done! All dashboards are corrected and live.")

if __name__ == "__main__":
    run_pipeline()
    sync()
