import json
import os

import pandas as pd


BASE_SLOPE = 113
GROSS_SCORE_HOLE_TOTAL_ISSUE = "gross_score_hole_total_mismatch"


def normalize_course_columns(course_df):
    normalized = course_df.copy()
    normalized.columns = [str(column).strip().lower() for column in normalized.columns]
    return normalized


def build_hole_map(course_df):
    normalized = normalize_course_columns(course_df)
    hole_map = {}

    for _, row in normalized.iterrows():
        hole_value = row.get('hole')
        try:
            hole_num = int(str(hole_value).replace('H', '').replace('h', ''))
        except (TypeError, ValueError):
            continue

        par_value = pd.to_numeric(row.get('par'), errors='coerce')
        stroke_index_value = pd.to_numeric(row.get('hi'), errors='coerce')
        if pd.isna(par_value) or pd.isna(stroke_index_value):
            continue

        hole_map[hole_num] = {
            'par': int(par_value),
            'si': int(stroke_index_value),
        }

    return hole_map


def normalize_scores_columns(scores_df):
    normalized = scores_df.copy()
    if 'Round_Handicap' in normalized.columns and 'Differential' not in normalized.columns:
        normalized = normalized.rename(columns={'Round_Handicap': 'Differential'})
    return normalized


def load_score_analysis_exclusions(base_dir):
    exceptions_path = os.path.join(base_dir, 'data', 'score_audit_exceptions.csv')
    if not os.path.exists(exceptions_path):
        return set()

    exceptions = pd.read_csv(exceptions_path)
    required_cols = {'Date', 'Player', 'Issue'}
    if exceptions.empty or not required_cols.issubset(exceptions.columns):
        return set()

    issue_mask = exceptions['Issue'].astype(str) == GROSS_SCORE_HOLE_TOTAL_ISSUE
    if 'Status' in exceptions.columns:
        issue_mask &= exceptions['Status'].astype(str).str.lower().ne('resolved')

    return set(
        map(
            tuple,
            exceptions.loc[issue_mask, ['Date', 'Player']]
            .fillna('')
            .astype(str)
            .itertuples(index=False, name=None),
        )
    )


def strokes_received_for_hole(course_handicap, hole_si):
    if pd.isna(course_handicap):
        return None

    rounded_handicap = int(round(float(course_handicap)))
    sign = 1 if rounded_handicap >= 0 else -1
    absolute_handicap = abs(rounded_handicap)

    base_strokes = absolute_handicap // 18
    extra_holes = absolute_handicap % 18
    strokes = base_strokes
    if extra_holes and hole_si <= extra_holes:
        strokes += 1

    return strokes * sign


def calculate_net_score(gross, hole_si, course_handicap):
    if pd.isna(gross):
        return None

    strokes_received = strokes_received_for_hole(course_handicap, hole_si)
    if strokes_received is None:
        return None

    return float(gross) - strokes_received


def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    scores_path = os.path.join(base_dir, 'data', 'scores.csv')
    handicaps_path = os.path.join(base_dir, 'data', 'handicaps.csv')
    course_path = os.path.join(base_dir, 'data', 'course_info.csv')
    output_path = os.path.join(base_dir, 'website', 'data', 'methodology_data.json')

    scores_df = normalize_scores_columns(pd.read_csv(scores_path))
    handicaps_df = pd.read_csv(handicaps_path)
    course_df = pd.read_csv(course_path)

    scores_df['Date'] = pd.to_datetime(scores_df['Date'])
    handicaps_df['Date'] = pd.to_datetime(handicaps_df['Date'])
    exclusions = load_score_analysis_exclusions(base_dir)
    if exclusions:
        keep_mask = ~scores_df.apply(
            lambda row: (
                row['Date'].strftime('%Y-%m-%d'),
                str(row['Player']),
            ) in exclusions,
            axis=1,
        )
        excluded_count = int((~keep_mask).sum())
        scores_df = scores_df[keep_mask].copy()
        if excluded_count:
            print(f"Excluded {excluded_count} unresolved historical score row(s) from methodology analysis.")
    if 'Handicap_Index' in handicaps_df.columns:
        handicaps_df['Handicap_Index'] = pd.to_numeric(handicaps_df['Handicap_Index'], errors='coerce')
    if 'Course_Handicap' in handicaps_df.columns:
        handicaps_df['Course_Handicap'] = pd.to_numeric(handicaps_df['Course_Handicap'], errors='coerce')

    hole_map = build_hole_map(course_df)
    players = sorted(scores_df['Player'].dropna().unique())
    data_export = {}

    for player in players:
        player_rounds = scores_df[scores_df['Player'] == player].copy()
        player_hcp = handicaps_df[handicaps_df['Player'] == player].sort_values('Date')
        hole_stats = {hole: {'gross_sum': 0.0, 'net_sum': 0.0, 'count': 0} for hole in range(1, 19)}

        for _, row in player_rounds.iterrows():
            round_hcp = player_hcp[player_hcp['Date'] == row['Date']]
            course_handicap = round_hcp.iloc[0]['Course_Handicap'] if not round_hcp.empty else pd.NA

            for hole in range(1, 19):
                hole_info = hole_map.get(hole)
                if not hole_info:
                    continue

                score_col = f'H{hole}'
                gross = pd.to_numeric(row.get(score_col), errors='coerce')
                if pd.isna(gross) or pd.isna(course_handicap):
                    continue

                net = calculate_net_score(gross, hole_info['si'], course_handicap)
                if net is None:
                    continue

                hole_stats[hole]['gross_sum'] += float(gross)
                hole_stats[hole]['net_sum'] += float(net)
                hole_stats[hole]['count'] += 1

        latest_hcp = player_hcp.iloc[-1] if not player_hcp.empty else None
        latest_hi = (
            round(float(latest_hcp['Handicap_Index']), 1)
            if latest_hcp is not None and pd.notna(latest_hcp.get('Handicap_Index'))
            else None
        )
        latest_ch = (
            round(float(latest_hcp['Course_Handicap']), 1)
            if latest_hcp is not None and pd.notna(latest_hcp.get('Course_Handicap'))
            else None
        )

        player_hole_data = []
        for hole in range(1, 19):
            stats = hole_stats[hole]
            if stats['count'] == 0 or hole not in hole_map:
                continue

            avg_gross = stats['gross_sum'] / stats['count']
            avg_net = stats['net_sum'] / stats['count']
            par = hole_map[hole]['par']
            net_diff = avg_net - par

            if net_diff < -0.5:
                status = 'Strength'
                status_class = 'text-green-600 font-bold'
            elif net_diff > 0.5:
                status = 'Weakness'
                status_class = 'text-red-600 font-bold'
            else:
                status = 'Neutral'
                status_class = 'text-gray-500'

            player_hole_data.append({
                'hole': hole,
                'par': par,
                'si': hole_map[hole]['si'],
                'avg_gross': round(avg_gross, 2),
                'avg_net': round(avg_net, 2),
                'net_diff': round(net_diff, 2),
                'status': status,
                'status_class': status_class,
            })

        data_export[player] = {
            'rounds_analyzed': int(len(player_rounds)),
            'latest_hi': latest_hi,
            'latest_ch': latest_ch,
            'holes': player_hole_data,
        }

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w') as output_file:
        json.dump(data_export, output_file, indent=2)

    print(f"Analysis generated for {len(players)} players at {output_path}")


if __name__ == "__main__":
    main()
