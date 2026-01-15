import pandas as pd
import glob
import os
import json
from google.colab import drive

# --- STEP 1: MOUNT DRIVE ---
drive.mount('/content/drive', force_remount=True)

# --- STEP 2: SETUP & LOADING ---
base_path = '/content/drive/MyDrive/001-SG-SG/Inputs'
output_folder = '/content/drive/MyDrive/001-SG-SG/colab/Outputs'
website_folder = '/content/drive/MyDrive/001-SG-SG/colab/Outputs/Website_Snippets'

# Ensure folders exist
for folder in [output_folder, website_folder]:
    if not os.path.exists(folder):
        os.makedirs(folder)

print(f"Scanning folder: {base_path}...\n")

# 1. LOAD STATIC SCORECARD CSV
scorecard_path = os.path.join(base_path, 'SG-SG_Data - Scorecard.csv')
if os.path.exists(scorecard_path):
    scorecard = pd.read_csv(scorecard_path)
    print(f"✅ SCORECARD loaded: {os.path.basename(scorecard_path)}")
else:
    # Fallback check
    old_scorecard_path = os.path.join(base_path, 'SG-SG_Data_Tables - Scorecard.csv')
    if os.path.exists(old_scorecard_path):
        scorecard = pd.read_csv(old_scorecard_path)
        print(f"✅ SCORECARD loaded (old name): {os.path.basename(old_scorecard_path)}")
    else:
        print(f"❌ ERROR: Scorecard file not found.")
        scorecard = pd.DataFrame()

# 2. LOAD EXCEL FILES
excel_files = glob.glob(os.path.join(base_path, "*.xlsx"))
print(f"found {len(excel_files)} Excel files.")

# Updated Dictionary to include 'BB' and 'Quota'
dfs = {
    'RawScores': [], 'NetMedal': [],
    'Team': [], 'BB': [],       # Handle both Legacy 'Team' and new 'BB'
    'Quota': [],                # New Quota Tab
    'GrossSkins': [], 'NetSkins': [], 'Handicaps': []
}

for f in excel_files:
    print(f"  Processing: {os.path.basename(f)}")
    try:
        xls = pd.read_excel(f, sheet_name=None)
        for key in dfs.keys():
            # Check for exact match or case-insensitive match if needed
            if key in xls:
                dfs[key].append(xls[key])
    except Exception as e:
        print(f"  ⚠️ Error reading {os.path.basename(f)}: {e}")

# Concatenate
master = {}
for key, data_list in dfs.items():
    if data_list:
        master[key] = pd.concat(data_list, ignore_index=True)
    else:
        master[key] = pd.DataFrame()

# Assign variables
raw_scores = master['RawScores']
net_medal = master['NetMedal']
gross_skins = master['GrossSkins']
net_skins = master['NetSkins']
handicaps = master['Handicaps']

# --- HANDLE TAB NAME MIGRATION (TEAM -> BB) ---
# We normalize column names before merging so they stack correctly
legacy_team = master['Team'].copy()
new_bb = master['BB'].copy()

# Rename columns in Legacy Team to match standard "Best Ball" naming
# Assumption: Legacy had 'Team_net', 'Team_earnings'
legacy_team.rename(columns={
    'Team_net': 'Best_Ball_Net',
    'Team_earnings': 'Best_Ball_Earnings'
}, inplace=True)

# Rename columns in New BB to match standard "Best Ball" naming
# Assumption: New tab might be 'BB_net', 'BB_earnings' or similar.
# We'll normalize any column with 'earnings' to 'Best_Ball_Earnings' if not already done.
for col in new_bb.columns:
    if 'earnings' in col.lower() and 'Best_Ball' not in col:
        new_bb.rename(columns={col: 'Best_Ball_Earnings'}, inplace=True)
    if 'net' in col.lower() and 'Best_Ball' not in col:
        new_bb.rename(columns={col: 'Best_Ball_Net'}, inplace=True)

# Combine Legacy and New
best_ball_df = pd.concat([legacy_team, new_bb], ignore_index=True)

# --- HANDLE QUOTA ---
quota_df = master['Quota'].copy()
# Normalize Quota columns (Look for 'earnings')
for col in quota_df.columns:
    if 'earnings' in col.lower():
        quota_df.rename(columns={col: 'Quota_Earnings'}, inplace=True)

# --- STEP 3: PRE-CLEANING & DATE STANDARDIZATION ---
for df_temp in [raw_scores, net_medal, best_ball_df, quota_df, gross_skins, net_skins, handicaps]:
    if not df_temp.empty:
        for date_col in ['Date', 'date']:
            if date_col in df_temp.columns:
                df_temp[date_col] = pd.to_datetime(df_temp[date_col], errors='coerce')

# --- STEP 4: DATA QUALITY CHECK ---
print("\n--- 🔍 DATA QUALITY REPORT ---")
issues_found = False

# Check 1: Gross Scores
if not raw_scores.empty and 'Gross_Score' in raw_scores.columns:
    temp_check = pd.to_numeric(raw_scores['Gross_Score'], errors='coerce')
    bad_gross = raw_scores[temp_check.isna() & raw_scores['Gross_Score'].notna()]
    if not bad_gross.empty:
        print(f"⚠️ WARNING: Found {len(bad_gross)} invalid Gross Scores.")
        issues_found = True
elif raw_scores.empty:
    print("⚠️ WARNING: RawScores DataFrame is empty. Cannot check Gross Scores.")
    issues_found = True # Consider this an issue if data is expected
else:
    print("⚠️ WARNING: 'Gross_Score' column not found in RawScores. Cannot check Gross Scores.")
    issues_found = True

if not issues_found:
    print("✅ No data format errors found.")
else:
    print("❌ PLEASE FIX ERRORS IN EXCEL FILES or ensure files are present.")

# --- STEP 5: CLEANING & CALCULATION ---
def clean_currency(x):
    if isinstance(x, str):
        cleaned_x = x.replace('$', '').replace(',', '').replace(' ', '')
        try:
            return float(cleaned_x)
        except ValueError:
            return 0.0
    return x if isinstance(x, (int, float)) else 0.0

def clean_placement(x):
    if isinstance(x, str):
        clean_str = x.upper().replace('T', '').strip()
        if clean_str.isdigit():
            return int(clean_str)
    return x

# Apply Cleaning
if not net_medal.empty:
    net_medal['net_medal_earnings'] = net_medal['net_medal_earnings'].apply(clean_currency)
    if 'Placement' in net_medal.columns:
        net_medal['Placement'] = net_medal['Placement'].apply(clean_placement)

if not best_ball_df.empty:
    # Check for the column we normalized earlier
    if 'Best_Ball_Earnings' in best_ball_df.columns:
        best_ball_df['Best_Ball_Earnings'] = best_ball_df['Best_Ball_Earnings'].apply(clean_currency)
    if 'Placement' in best_ball_df.columns:
        best_ball_df['Placement'] = best_ball_df['Placement'].apply(clean_placement)

if not quota_df.empty:
    if 'Quota_Earnings' in quota_df.columns:
        quota_df['Quota_Earnings'] = quota_df['Quota_Earnings'].apply(clean_currency)
    if 'Placement' in quota_df.columns:
        quota_df.rename(columns={col: 'Quota_Earnings'}, inplace=True)
    if 'Placement' in quota_df.columns:
        quota_df['Placement'] = quota_df['Placement'].apply(clean_placement)

if not gross_skins.empty:
    gross_skins['Gskins_earnings'] = gross_skins['Gskins_earnings'].apply(clean_currency)

if not net_skins.empty:
    net_skins['Nskins_earnings'] = net_skins['Nskins_earnings'].apply(clean_currency)

# Initialize df and consolidated_table as empty DataFrames to avoid errors if raw_scores is empty
df = pd.DataFrame()
consolidated_table = pd.DataFrame()
player_dashboard = pd.DataFrame()
hole_by_hole = pd.DataFrame()
hole_view = pd.DataFrame()

# Only proceed if raw_scores has data and the necessary 'Gross_Score' column
if not raw_scores.empty and 'Gross_Score' in raw_scores.columns:
    # Rename Columns for Merging
    base = raw_scores.rename(columns={'Name': 'Player', 'Date': 'date'})
    if not handicaps.empty:
        handicaps = handicaps.rename(columns={'Date': 'date', 'Course_Handicap': 'playing_handicap'})

    # Merge Handicaps
    if not handicaps.empty:
        base = pd.merge(base, handicaps[['date', 'Player', 'HI', 'playing_handicap']],
                        on=['date', 'Player'], how='left')
    else:
        # If handicaps is empty, add default columns to base if it's not empty already
        if not base.empty:
            base['HI'] = 0
            base['playing_handicap'] = 0

    if not base.empty and 'Gross_Score' in base.columns:
        # Force Numeric
        base['Gross_Score'] = pd.to_numeric(base['Gross_Score'], errors='coerce')
        base['playing_handicap'] = pd.to_numeric(base['playing_handicap'], errors='coerce')
        base['net_score'] = base['Gross_Score'] - base['playing_handicap']

        # Merge Tournament Tables
        df = pd.merge(base, net_medal[['date', 'Player', 'Placement', 'net_tot', 'net_medal_earnings']],
                      on=['date', 'Player'], how='left')
        df = df.rename(columns={'Placement': 'Net Medal Place', 'net_tot': 'Net Medal Net', 'net_medal_earnings': 'Net Medal Earn ($)'})

        # Merge Best Ball (Combined Team/BB)
        if 'Best_Ball_Earnings' in best_ball_df.columns:
            df = pd.merge(df, best_ball_df[['date', 'Player', 'Placement', 'Best_Ball_Net', 'Best_Ball_Earnings']],
                          on=['date', 'Player'], how='left')
            df = df.rename(columns={'Placement': 'Best Ball Place', 'Best_Ball_Net': 'Best Ball Net', 'Best_Ball_Earnings': 'Best Ball Earn ($)'})
        else:
            df['Best Ball Earn ($)'] = 0

        # Merge Quota
        if not quota_df.empty and 'Quota_Earnings' in quota_df.columns:
            # Select cols to merge (add Placement or Points if available in Quota tab)
            cols_to_merge = ['date', 'Player', 'Quota_Earnings']
            if 'Placement' in quota_df.columns:
                cols_to_merge.append('Placement')

            df = pd.merge(df, quota_df[cols_to_merge], on=['date', 'Player'], how='left')
            df = df.rename(columns={'Placement': 'Quota Place', 'Quota_Earnings': 'Quota Earn ($)'})
        else:
            df['Quota Earn ($)'] = 0

        # Merge Skins
        df = pd.merge(df, gross_skins[['date', 'Player', 'Gskins_count', 'Gskins_earnings']],
                      on=['date', 'Player'], how='left')
        df = df.rename(columns={'Gskins_count': 'Gross Skins Count', 'Gskins_earnings': 'Gross Skins Earn ($)'})

        df = pd.merge(df, net_skins[['date', 'Player', 'Nskins_count', 'Nskins_earnings']],
                      on=['date', 'Player'], how='left')
        df = df.rename(columns={'Nskins_count': 'Net Skins Count', 'Nskins_earnings': 'Net Skins Earn ($)'})

        # Fill Zeros
        cols_to_fill = ['Net Medal Earn ($)', 'Best Ball Earn ($)', 'Quota Earn ($)', 'Gross Skins Earn ($)', 'Net Skins Earn ($)']
        # Create cols if they don't exist (safety)
        for c in cols_to_fill:
            if c not in df.columns:
                df[c] = 0.0

        df[cols_to_fill] = df[cols_to_fill].fillna(0)

        df['Total Earnings ($)'] = (df['Net Medal Earn ($)'] +
                                    df['Best Ball Earn ($)'] +
                                    df['Quota Earn ($)'] +
                                    df['Gross Skins Earn ($)'] +
                                    df['Net Skins Earn ($)'])

        # Calculate Tournament Year
        df['Tournament_Year'] = df['date'].apply(lambda x: x.year + 1 if x.month >= 11 else x.year)

        consolidated_table = df.rename(columns={'Gross_Score': 'Gross Score Total'})
    else:
        print("❌ WARNING: 'Gross_Score' column not found in the processed base DataFrame. Skipping consolidated table generation.")
else:
    print("❌ WARNING: No raw scores data loaded or 'Gross_Score' column is missing. Skipping consolidated table generation and further calculations.")

# --- STEP 6: GENERATE DASHBOARD OUTPUTS ---

# 1. Player Stats (For PlayerStats.html)
if not consolidated_table.empty and 'Player' in consolidated_table.columns and 'Gross Score Total' in consolidated_table.columns and 'net_score' in consolidated_table.columns:
    if not scorecard.empty and 'Par' in scorecard.columns:
        total_par = scorecard['Par'].sum()
    else:
        total_par = 72

    player_stats_agg = consolidated_table.groupby('Player').agg({
        'Gross Score Total': 'mean',
        'net_score': 'mean'
    }).reset_index()

    player_stats_agg['Net to Par'] = player_stats_agg['net_score'] - total_par

    # Rename columns to match website EXACTLY
    player_dashboard = player_stats_agg.rename(columns={
        'Player': 'Name',
        'Gross Score Total': 'Average Gross Score',
        'net_score': 'Average Net Score'
    })
    player_dashboard = player_dashboard[['Name', 'Average Gross Score', 'Average Net Score', 'Net to Par']].round(2)
else:
    print("❌ WARNING: Consolidated table is empty or missing required columns for Player Stats. Skipping.")

# 2. Hole Data (For AverageScore.html and HoleIndex.html)
if not raw_scores.empty and not scorecard.empty and 'Name' in raw_scores.columns and 'Date' in raw_scores.columns and 'Par' in scorecard.columns:
    hole_cols = [c for c in raw_scores.columns if c.startswith('H') and c != 'HI']
    if hole_cols:
        melted = raw_scores.melt(id_vars=['Name', 'Date'], value_vars=hole_cols, var_name='Hole', value_name='Score')
        melted['Score'] = pd.to_numeric(melted['Score'], errors='coerce')
        hole_by_hole = pd.merge(melted, scorecard, on='Hole', how='left')
        hole_by_hole['Score vs Par'] = hole_by_hole['Score'] - hole_by_hole['Par']

        # Ensure 'HI' column exists in hole_by_hole before grouping
        if 'HI' not in hole_by_hole.columns:
            hole_by_hole['HI'] = 0 # Default value if not available

        hole_view = hole_by_hole.groupby(['Hole', 'Par', 'Yardage', 'HI']).agg({
            'Score': 'mean',
            'Score vs Par': 'mean'
        }).reset_index()

        hole_view['SG-SG Handicap'] = hole_view['Score vs Par'].rank(ascending=False)
        hole_view = hole_view.rename(columns={'HI': 'Handicap'})
        hole_view = hole_view.sort_values('SG-SG Handicap')
    else:
        print("❌ WARNING: No hole columns found in raw scores. Skipping hole data analysis.")
else:
    print("❌ WARNING: Raw scores or scorecard data missing or incomplete for hole-by-hole analysis. Skipping.")

# 3. Money List (For MoneyList2025.html)
# Rename columns to match HTML "csvData" headers EXACTLY
money_cols_map = {
    'Player': 'Name',
    'Best Ball Earn ($)': 'Best_Ball_Earnings',
    'Quota Earn ($)': 'Quota_Earnings',    # NEW COLUMN
    'Net Skins Earn ($)': 'Net_Skins_Earnings',
    'Gross Skins Earn ($)': 'Gross_Skins_Earnings',
    'Net Medal Earn ($)': 'Net_Earnings',
    'Total Earnings ($)': 'Total Earnings'
}

# --- STEP 7: OUTPUT GENERATION ---
print("\n--- 💾 SAVING FILES ---")

def save_csv(df, filename_base):
    if not df.empty:
        csv_path = os.path.join(output_folder, f"{filename_base}.csv")
        df.to_csv(csv_path, index=False)
        print(f"  -> Saved CSV: {filename_base}.csv")
    else:
        print(f"  -> Skipped saving {filename_base}.csv as DataFrame is empty.")

def save_snippet(content, filename):
    path = os.path.join(website_folder, filename)
    with open(path, 'w') as f:
        f.write(content)
    print(f"  -> Generated Website Snippet: {filename}")

# Save Standard CSVs
save_csv(consolidated_table, 'SG_SG_Consolidated_Data')
save_csv(player_dashboard, 'Dashboard_PlayerStats')
save_csv(hole_view, 'Dashboard_HoleStats')

# --- GENERATE WEBSITE SNIPPETS ---

# 1. PLAYER STATS
if not player_dashboard.empty:
    player_csv_string = player_dashboard.to_csv(index=False)
    save_snippet(player_csv_string, 'PlayerStats_Snippet.txt')
else:
    save_snippet("", 'PlayerStats_Snippet.txt') # Save an empty file or a default empty content
    print("  -> Skipped generating PlayerStats_Snippet.txt as player_dashboard is empty.")

# 2. HOLE AVERAGE
if not hole_view.empty:
    hole_js_data = []
    for _, row in hole_view.iterrows():
        h_val = row['Hole']
        if isinstance(h_val, str) and h_val.startswith('H'):
            try:
                h_val = int(h_val.replace('H', ''))
            except:
                pass
        hole_js_data.append({
            'hole': h_val,
            'score': round(row['Score'], 2),
            'par': int(row['Par'])
        })
    hole_snippet = f"const holeData = {json.dumps(hole_js_data, indent=4)};"
    save_snippet(hole_snippet, 'HoleAverage_Snippet.js')
else:
    save_snippet("const holeData = [];", 'HoleAverage_Snippet.js')
    print("  -> Skipped generating HoleAverage_Snippet.js as hole_view is empty.")

# 3. HOLE INDEX
if not hole_view.empty:
    index_js_data = []
    for _, row in hole_view.iterrows():
        h_val = row['Hole']
        if isinstance(h_val, str) and h_val.startswith('H'):
            try:
                h_val = int(h_val.replace('H', ''))
            except:
                pass
        index_js_data.append({
            'hole': h_val,
            'x': int(row['Handicap']),
            'y': int(row['SG-SG Handicap'])
        })
    index_snippet = f"const rawData = {json.dumps(index_js_data, indent=4)};"
    save_snippet(index_snippet, 'HoleIndex_Snippet.js')
else:
    save_snippet("const rawData = [];", 'HoleIndex_Snippet.js')
    print("  -> Skipped generating HoleIndex_Snippet.js as hole_view is empty.")

# 4. MONEY LIST
if not consolidated_table.empty and 'Tournament_Year' in consolidated_table.columns:
    unique_years = consolidated_table['Tournament_Year'].dropna().unique()
    if unique_years.size > 0:
        for year in sorted(unique_years):
            year_int = int(year)
            df_year = consolidated_table[consolidated_table['Tournament_Year'] == year_int]

            # Ensure all columns exist before selecting and are numeric for aggregation
            cols_to_select = ['Player'] + [k for k in money_cols_map.keys() if k != 'Player']
            cols_to_select = [c for c in cols_to_select if c in df_year.columns]

            if len(cols_to_select) > 1: # Ensure there are columns other than 'Player' for aggregation
                # Convert selected earnings columns to numeric, handling errors by coercing to NaN then filling with 0
                for col in cols_to_select[1:]:
                    df_year[col] = pd.to_numeric(df_year[col], errors='coerce').fillna(0)

                money_view = df_year.groupby('Player')[cols_to_select[1:]].sum().reset_index()
                money_view = money_view.rename(columns=money_cols_map)
                # Ensure 'Total Earnings' is created and exists before sorting
                if 'Total Earnings' in money_view.columns:
                    money_view = money_view.sort_values('Total Earnings', ascending=False)

                save_csv(money_view, f'Dashboard_Money_{year_int}')

                money_csv_string = money_view.to_csv(index=False)
                save_snippet(money_csv_string, f'MoneyList_{year_int}_Snippet.txt')
            else:
                print(f"  -> Skipped generating MoneyList_{year_int}_Snippet.txt as no relevant earning columns found for {year_int} data.")
                save_snippet("", f'MoneyList_{year_int}_Snippet.txt')
    else:
        print("  -> Skipped generating Money List snippets as no unique tournament years found in consolidated data.")
        save_snippet("", 'MoneyList_Empty.txt')
else:
    print("  -> Skipped generating Money List snippets as consolidated_table is empty or missing 'Tournament_Year' column.")
    save_snippet("", 'MoneyList_Empty.txt')

print(f"\n✅ DONE! All website update files are in: {website_folder}")