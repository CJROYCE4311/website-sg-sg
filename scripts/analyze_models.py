import pandas as pd
import datetime

# Configuration
COURSE_RATING = 70.5
SLOPE_RATING = 124
SCORES_FILE = 'data/scores.csv'
MONTHS_LOOKBACK = 13

def calculate_differential(score):
    return (score - COURSE_RATING) * 113 / SLOPE_RATING

def get_affected_players():
    # Load Data
    try:
        df = pd.read_csv(SCORES_FILE, parse_dates=['Date'])
    except FileNotFoundError:
        print("Error: scores.csv not found.")
        return

    # Filter by Date (Last 13 Months)
    cutoff_date = datetime.datetime.now() - datetime.timedelta(days=MONTHS_LOOKBACK*30)
    df = df[df['Date'] >= cutoff_date]

    results_last2 = []
    results_best3 = []

    for player, group in df.groupby('Player'):
        rounds = len(group)
        if rounds < 1: continue

        # Get Current Index (from latest round entry)
        latest_round = group.sort_values('Date', ascending=False).iloc[0]
        current_hcp = float(latest_round['Round_Handicap']) if 'Round_Handicap' in latest_round and pd.notna(latest_round['Round_Handicap']) else 0.0

        # Calculate Differentials
        group['Differential'] = group['Gross_Score'].apply(calculate_differential)
        
        # Sort by Date for Last 2
        group_date_sorted = group.sort_values('Date', ascending=False)
        last2_rounds = group_date_sorted.head(2)
        last2_diffs = last2_rounds['Differential'].tolist()
        last2_scores = last2_rounds['Gross_Score'].tolist()
        
        # Sort by Differential for Best 3
        diffs = group['Differential'].tolist()
        diffs.sort()
        best3_diffs = diffs[:3]
        
        # Need to find the Scores corresponding to these specific best 3 differentials
        # We can't just take the 3 lowest scores because Course/Slope might vary (though currently constant)
        # For this specific project, since Rating/Slope is constant, Lowest Diff = Lowest Score.
        best3_scores = sorted(group['Gross_Score'].tolist())[:3]

        # Calculate Implied Indices
        implied_last2 = sum(last2_diffs) / len(last2_diffs) if last2_diffs else 0
        implied_best3 = sum(best3_diffs) / len(best3_diffs) if best3_diffs else 0

        # Check for Downward Adjustment (Implied < Current)
        # We use a small threshold (e.g. -0.1) to avoid floating point noise, or strictly <
        
        # Last 2 Model
        if implied_last2 < current_hcp:
            results_last2.append({
                'player': player,
                'current': current_hcp,
                'implied': round(implied_last2, 1),
                'diff': round(implied_last2 - current_hcp, 1),
                'scores': [int(s) for s in last2_scores]
            })

        # Best 3 Model
        if implied_best3 < current_hcp:
             results_best3.append({
                'player': player,
                'current': current_hcp,
                'implied': round(implied_best3, 1),
                'diff': round(implied_best3 - current_hcp, 1),
                'scores': [int(s) for s in best3_scores]
            })

    # Sort by Adjustment Magnitude (Most negative first)
    results_last2.sort(key=lambda x: x['diff'])
    results_best3.sort(key=lambda x: x['diff'])

    return results_last2, results_best3

if __name__ == "__main__":
    l2, b3 = get_affected_players()
    
    print("--- LAST 2 (TREND) ---")
    for p in l2:
        print(f"{p['player']}|{p['current']}|{p['implied']}|{p['diff']}|{p['scores']}")
        
    print("\n--- BEST 3 (POTENTIAL) ---")
    for p in b3:
        print(f"{p['player']}|{p['current']}|{p['implied']}|{p['diff']}|{p['scores']}")
