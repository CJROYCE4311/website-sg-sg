import pandas as pd
import os
import numpy as np
from datetime import timedelta

# ==========================================
# ⚙️ CONFIGURATION
# ==========================================
COURSE_RATING = 70.5
SLOPE_RATING = 124
PAR = 72
MONTHS_LOOKBACK = 13  # Analysis window
# ==========================================

print(f"--- ⛳ STARTING COMMITTEE HANDICAP REVIEW (DUAL ANALYSIS) ---")

# 1. GET DATA
try:
    # Check if consolidated_table exists in memory (for Canvas/Notebook environments)
    df_analysis = consolidated_table.copy()
    print("✅ Loaded data from memory.")
except NameError:
    # Fallback: Load from CSV
    csv_path = '/content/drive/MyDrive/001-SG-SG/colab/Outputs/SG_SG_Consolidated_Data.csv'
    if os.path.exists(csv_path):
        df_analysis = pd.read_csv(csv_path)
        print(f"✅ Loaded data from CSV: {csv_path}")
    else:
        # Mock Data Generation (Updated with recent dates to test date filtering)
        print("⚠️ 'consolidated_table' not found and CSV missing. Generating MOCK DATA...")
        today = pd.Timestamp.now()
        dates = [today - timedelta(days=x) for x in [10, 20, 40, 400, 10, 20, 50, 410]] # 400+ days is > 13 months
        data = {
            'date': dates,
            'Player': ['Chris Royce', 'Chris Royce', 'Chris Royce', 'Chris Royce',
                       'Mikki Royce', 'Mikki Royce', 'Mikki Royce', 'Mikki Royce'],
            'Gross Score Total': [78, 82, 75, 95, 90, 88, 85, 100],
            'playing_handicap': [6, 6, 6, 6, 15, 15, 15, 15],
            'net_score': [72, 76, 69, 89, 75, 73, 70, 85],
            'HI': [5.2, 5.2, 5.1, 5.5, 14.5, 14.5, 14.2, 14.8]
        }
        df_analysis = pd.DataFrame(data)

# 2. FILTER & PREP
required_cols = ['date', 'Player', 'Gross Score Total', 'playing_handicap', 'net_score']

# Ensure HI exists
if 'HI' not in df_analysis.columns:
    df_analysis['HI'] = 0.0

# Convert date and numeric columns
df_analysis['date'] = pd.to_datetime(df_analysis['date'])
df_analysis['HI'] = pd.to_numeric(df_analysis['HI'], errors='coerce').fillna(0)
df_analysis = df_analysis[df_analysis['Gross Score Total'] > 0].copy()

# 3. DATE FILTERING (13 MONTHS)
latest_date = df_analysis['date'].max()
cutoff_date = latest_date - pd.DateOffset(months=MONTHS_LOOKBACK)

print(f"📅 Data Range: {cutoff_date.date()} to {latest_date.date()} ({MONTHS_LOOKBACK} Months)")

# Filter data to time window
df_recent = df_analysis[df_analysis['date'] >= cutoff_date].copy()

# 4. CALCULATE DIFFERENTIAL
df_recent['Differential'] = (df_recent['Gross Score Total'] - COURSE_RATING) * (113 / SLOPE_RATING)
df_recent['Differential'] = df_recent['Differential'].round(1)

# 5. PERFORM ANALYSIS LOOP
details_list = []
summary_top3_list = []
summary_top6_list = []

grouped = df_recent.groupby('Player')

for player, group in grouped:
    rounds_count = len(group)

    # Needs at least 1 round in the last 13 months to be included (already handled by date filter)
    if rounds_count == 0:
        continue

    # A. Get Current Handicap Index (from most recent date in window)
    latest_round = group.sort_values(by='date', ascending=False).iloc[0]
    current_hi = latest_round['HI']

    # --- FUNCTION TO CALCULATE STATS ---
    def calculate_stats(df_group, top_n, current_index, total_rounds):
        # Sort by Net Score (Ascending) for best performance, then Date (Descending)
        # Note: Taking Top N best Net Scores
        top_perfs = df_group.sort_values(by=['net_score', 'date'], ascending=[True, False]).head(top_n).copy()

        avg_gross = top_perfs['Gross Score Total'].mean()
        avg_net = top_perfs['net_score'].mean()
        implied_index = top_perfs['Differential'].mean()

        note = f"Only had {total_rounds} rounds" if total_rounds < top_n else ""

        diff_temp = implied_index - current_index
        suggested_adj = diff_temp if diff_temp < 0 else 0

        return {
            'Player': player,
            f'Implied Index (Top {top_n})': round(implied_index, 1),
            'Current Index': round(current_index, 1),
            'Suggested Adjustment': round(suggested_adj, 1),
            f'Avg Gross (Top {top_n})': round(avg_gross, 1),
            f'Avg Net (Top {top_n})': round(avg_net, 1),
            'Total_Rounds_13Mo': total_rounds,
            'Notes': note
        }

    # B. Calculate Top 3 Stats
    stats_3 = calculate_stats(group, 3, current_hi, rounds_count)
    summary_top3_list.append(stats_3)

    # C. Calculate Top 6 Stats
    stats_6 = calculate_stats(group, 6, current_hi, rounds_count)
    summary_top6_list.append(stats_6)

    # D. Add to Details List (All rounds in window)
    all_player_rounds = group.sort_values(by='date', ascending=False)
    for _, row in all_player_rounds.iterrows():
        details_list.append({
            'Player': player,
            'Date': row['date'].strftime('%Y-%m-%d'),
            'Gross Score': row['Gross Score Total'],
            'HCP Used': row['playing_handicap'],
            'Net Score': row['net_score'],
            'Round Differential': row['Differential'],
            'Total_Rounds_13Mo': rounds_count
        })

# 6. CREATE & SORT DATAFRAMES
def process_summary_df(data_list, top_n):
    df = pd.DataFrame(data_list)
    if df.empty:
        return df
    # Sort by Suggested Adjustment (lowest first)
    df = df.sort_values(by=['Suggested Adjustment', f'Implied Index (Top {top_n})'], ascending=[True, True])
    return df

df_summary_3 = process_summary_df(summary_top3_list, 3)
df_summary_6 = process_summary_df(summary_top6_list, 6)
df_details = pd.DataFrame(details_list)

# 7. OUTPUT
output_folder = '/content/drive/MyDrive/001-SG-SG/colab/Outputs'
if not os.path.exists(output_folder):
    output_folder = '.' # Fallback to current dir

path_3 = os.path.join(output_folder, 'Committee_Review_Summary_Top3.csv')
path_6 = os.path.join(output_folder, 'Committee_Review_Summary_Top6.csv')
path_details = os.path.join(output_folder, 'Committee_Review_Details.csv')

df_summary_3.to_csv(path_3, index=False)
df_summary_6.to_csv(path_6, index=False)
df_details.to_csv(path_details, index=False)

print("\n--- ✅ ANALYSIS COMPLETE ---")
print(f"1. Top 3 Summary saved to: {path_3}")
print(f"2. Top 6 Summary saved to: {path_6}")
print(f"3. Details saved to: {path_details}")

if not df_summary_3.empty:
    print("\n--- PREVIEW: TOP 3 ANALYSIS (Flagged Players) ---")
    print(df_summary_3[df_summary_3['Suggested Adjustment'] < 0].head().to_string(index=False))