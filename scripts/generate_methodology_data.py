import pandas as pd
import json
import os
import sys

# Add the scripts directory to the python path to import tournament_analyzer if needed
# But I will re-implement the specific row-by-row logic here to handle historical HI
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Constants
RATING = 70.5
SLOPE = 124
PAR = 72

def calculate_course_handicap(index, slope, rating, par):
    if pd.isna(index) or index == '':
        return 0
    val = float(index) * (slope / 113) + (rating - par)
    return int(round(val))

def calculate_net_score(gross, hole_si, course_handicap):
    if pd.isna(gross):
        return None
    
    strokes = course_handicap // 18
    remainder = course_handicap % 18
    
    if remainder >= hole_si:
        strokes += 1
        
    return gross - strokes

def main():
    # Paths
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    scores_path = os.path.join(base_dir, 'data', 'scores.csv')
    course_path = os.path.join(base_dir, 'data', 'course_info.csv')
    output_path = os.path.join(base_dir, 'website', 'data', 'methodology_data.json')
    
    # Load Data
    scores_df = pd.read_csv(scores_path)
    course_df = pd.read_csv(course_path)
    
    # Process Course Data
    # Map H1 -> 1, HI -> Stroke Index
    hole_map = {} # { 1: {'par': 4, 'si': 5}, ... }
    for _, row in course_df.iterrows():
        hole_str = row['Hole'] # "H1"
        try:
            hole_num = int(hole_str.replace('H', ''))
            hole_map[hole_num] = {
                'par': int(row['Par']),
                'si': int(row['HI'])
            }
        except ValueError:
            continue
            
    # Process Scores
    # We want to aggregate by Player
    players = scores_df['Player'].unique()
    
    data_export = {}
    
    for player in players:
        player_rounds = scores_df[scores_df['Player'] == player]
        
        # We need to calculate Net Score for every hole in every round
        # Because HI changes per round
        
        hole_stats = {h: {'gross_sum': 0, 'net_sum': 0, 'count': 0} for h in range(1, 19)}
        
        for _, row in player_rounds.iterrows():
            # Get HI for this round
            # scores.csv has 'Round_Handicap'
            round_hi = row.get('Round_Handicap', 0)
            ch = calculate_course_handicap(round_hi, SLOPE, RATING, PAR)
            
            for h in range(1, 19):
                col_name = f'H{h}'
                if col_name in row and pd.notna(row[col_name]):
                    gross = float(row[col_name])
                    si = hole_map[h]['si']
                    net = calculate_net_score(gross, si, ch)
                    
                    hole_stats[h]['gross_sum'] += gross
                    hole_stats[h]['net_sum'] += net
                    hole_stats[h]['count'] += 1
        
        # Calculate Averages and Status
        player_hole_data = []
        total_rounds = len(player_rounds)
        latest_hi = player_rounds.iloc[-1]['Round_Handicap'] if not player_rounds.empty else 0
        
        for h in range(1, 19):
            stats = hole_stats[h]
            if stats['count'] > 0:
                avg_gross = stats['gross_sum'] / stats['count']
                avg_net = stats['net_sum'] / stats['count']
                par = hole_map[h]['par']
                net_diff = avg_net - par
                
                # Status
                if net_diff < -0.5:
                    status = "Strength"
                    status_class = "text-green-600 font-bold"
                elif net_diff > 0.5:
                    status = "Weakness"
                    status_class = "text-red-600 font-bold"
                else:
                    status = "Neutral"
                    status_class = "text-gray-500"
                
                player_hole_data.append({
                    'hole': h,
                    'par': par,
                    'si': hole_map[h]['si'],
                    'avg_gross': round(avg_gross, 2),
                    'avg_net': round(avg_net, 2),
                    'net_diff': round(net_diff, 2),
                    'status': status,
                    'status_class': status_class
                })
        
        data_export[player] = {
            'rounds_analyzed': total_rounds,
            'latest_hi': latest_hi,
            'holes': player_hole_data
        }

    # Write to JSON
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(data_export, f, indent=2)
        
    print(f"Analysis generated for {len(players)} players at {output_path}")

if __name__ == "__main__":
    main()
