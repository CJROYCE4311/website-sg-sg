import pandas as pd
import os
import json
import re
import subprocess
import random
import argparse
import sys
from html import escape
from datetime import datetime
import warnings

warnings.filterwarnings("ignore")

# --- CONFIGURATION ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
WEBSITE_DIR = os.path.join(PROJECT_ROOT, "website")
PUBLISH_PATHS = ["data", "website"]

# CSV Paths
SCORES_FILE = os.path.join(DATA_DIR, "scores.csv")
FINANCIALS_FILE = os.path.join(DATA_DIR, "financials.csv")
HANDICAPS_FILE = os.path.join(DATA_DIR, "handicaps.csv")
COURSE_FILE = os.path.join(DATA_DIR, "course_info.csv")

# Constants
COURSE_RATING, SLOPE_RATING = 70.5, 124
COURSE_PAR = 72
BASE_SLOPE = 113
MONTHS_LOOKBACK = 13
FORMAT_DISPLAY_OVERRIDES = {
    "2026-03-21": {
        "format_name": "Stableford",
        "category_titles": {
            "NetMedal": "Stableford",
        },
    },
}

# --- BARSTOOL TEMPLATES ---
OPENERS = [
    "Alright folks, buckle up. Another Saturday at the Grove, another absolute electric factory of golf.",
    "What a day. What. A. Day. The boys were buzzing, the drinks were flowing (probably), and the scores? Well, let's talk about the scores.",
    "Pure chaos. That's the only way to describe the scene at Sterling Grove this weekend.",
    "Another classic SG@SG tilt is in the books. Legends were made, egos were bruised, and wallets were either fattened or decimated.",
    "If you weren't at the Grove this Saturday, you missed a generational display of grit, grind, and glory."
]

MIDDLERS = [
    "It was a bloodbath out there.",
    "Absolutely disgusting behavior from the leaderboard.",
    "You hate to see it, but you love to see it.",
    "Just guys being dudes, hitting fairways (occasionally) and draining putts.",
    "The golf gods were smiling down on a chosen few today."
]

CLOSERS = [
    "Go Green. Go White. See you on the next one.",
    "Stay dangerous.",
    "Kiss the ring.",
    "Don't let the door hit you on the way out.",
    "Viva la Stool... I mean, Viva la SG@SG."
]


def calculate_course_handicap(index_value):
    if pd.isna(index_value):
        return pd.NA
    return round(float(index_value) * SLOPE_RATING / BASE_SLOPE + (COURSE_RATING - COURSE_PAR), 1)


def ensure_handicap_columns(df):
    df = df.copy()

    if 'Handicap_Index' in df.columns:
        df['Handicap_Index'] = pd.to_numeric(df['Handicap_Index'], errors='coerce')
    if 'Course_Handicap' in df.columns:
        df['Course_Handicap'] = pd.to_numeric(df['Course_Handicap'], errors='coerce')

    if 'Course_Handicap' not in df.columns and 'Handicap_Index' in df.columns:
        df['Course_Handicap'] = df['Handicap_Index'].apply(calculate_course_handicap)
    elif 'Handicap_Index' in df.columns:
        missing_course = df['Course_Handicap'].isna() & df['Handicap_Index'].notna()
        df.loc[missing_course, 'Course_Handicap'] = df.loc[missing_course, 'Handicap_Index'].apply(calculate_course_handicap)

    return df


def ensure_scores_columns(df):
    df = df.copy()

    if 'Round_Handicap' in df.columns and 'Differential' not in df.columns:
        df = df.rename(columns={'Round_Handicap': 'Differential'})

    if 'Gross_Score' in df.columns:
        df['Gross_Score'] = pd.to_numeric(df['Gross_Score'], errors='coerce')
    if 'Differential' not in df.columns or df['Differential'].isna().any():
        df['Differential'] = ((df['Gross_Score'] - COURSE_RATING) * BASE_SLOPE / SLOPE_RATING).round(1)
    else:
        df['Differential'] = pd.to_numeric(df['Differential'], errors='coerce')

    return df

def get_barstool_writeup(date_str, format_name, winners_html):
    seeded_random = random.Random(f"{date_str}|{format_name}")
    opener = seeded_random.choice(OPENERS)
    middler = seeded_random.choice(MIDDLERS)
    closer = seeded_random.choice(CLOSERS)
    
    return f"""
    <div class="prose prose-lg text-gray-700 mx-auto">
        <p class="font-bold text-xl mb-4">{opener}</p>
        <p class="mb-4">We had ourselves a classic <strong>{format_name}</strong> showdown on {date_str}. {middler}</p>
        
        <div class="my-8 p-6 bg-gray-50 rounded-xl border border-gray-200 shadow-sm">
            <h3 class="text-2xl font-black text-gray-900 mb-4 border-b pb-2">THE WINNERS CIRCLE</h3>
            <div class="space-y-6">
                {winners_html}
            </div>
        </div>

        <p class="mb-6">To the victors go the spoils. To the losers? Better luck next time, pal. Hit the range.</p>
        <p class="font-bold italic text-right">{closer}</p>
    </div>
    """

def get_display_overrides(date_value):
    date_str = pd.to_datetime(date_value).strftime('%Y-%m-%d')
    return FORMAT_DISPLAY_OVERRIDES.get(date_str, {})

def get_category_title(date_value, category_key, default_title):
    overrides = get_display_overrides(date_value)
    return overrides.get('category_titles', {}).get(category_key, default_title)

def get_format_name(date_value, cats):
    overrides = get_display_overrides(date_value)
    if overrides.get('format_name'):
        return overrides['format_name']

    if 'Quota' in cats:
        return "Team Quota"
    if 'BestBall' in cats:
        return "Best Ball"
    if 'NetMedal' in cats:
        return "Net Medal"
    return "Tournament"

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
        # Using a safer replacement strategy that avoids swallowing subsequent code
        replacement = f"const {var_name} = `{content.strip()}`;";
        pattern = rf"const {var_name}\s*=\s*[`].*?[`];?"
    
    # Check if pattern exists before sub to avoid errors or silent failures
    if re.search(pattern, html, flags=re.DOTALL):
        new_html = re.sub(pattern, replacement, html, flags=re.DOTALL)
        with open(filepath, 'w') as f: f.write(new_html)
        print(f"✅ Updated {filename}")
    else:
        print(f"⚠️ Pattern for {var_name} not found in {filename}")

def get_latest_results_writeup(financials_df, scores_df):
    if financials_df.empty: return ""
    latest_date = financials_df['Date'].max()
    day_df = financials_df[financials_df['Date'] == latest_date].copy()
    date_str = latest_date.strftime('%Y-%m-%d')

    # Merge with scores to get Partner and Ranks
    rank_cols = ['Date', 'Player', 'Partner', 'Team_Rank', 'Individual_Rank']
    # Ensure Date is comparable
    scores_copy = scores_df.copy()
    scores_copy['Date'] = pd.to_datetime(scores_copy['Date'])
    day_scores = scores_copy[scores_copy['Date'] == latest_date][rank_cols]
    day_df = day_df.merge(day_scores, on=['Date', 'Player'], how='left')

    html = f"""
    <div class="mb-4 space-y-1">
        <h4 class="font-bold text-gray-900 text-lg m-0">Latest Tournament Recap</h4>
        <p class="text-sm m-0">Results for {date_str}.</p>
    </div>
    <div class="grid md:grid-cols-2 gap-x-8 gap-y-4 text-sm">
        <div class="space-y-4">
    """

    cat_map = {'BestBall': 'Best Ball', 'Quota': 'Team Quota', 'NetMedal': 'Net Medal'}
    for cat_key, default_title in cat_map.items():
        cat_df = day_df[day_df['Category'] == cat_key]
        if not cat_df.empty:
            cat_title = get_category_title(latest_date, cat_key, default_title)
            html += f"<div><h5 class='font-bold text-gray-900 mb-1 mt-0'>{cat_title}</h5><ul class='list-none pl-0 m-0 space-y-1'>"

            results = []
            if cat_key in ['BestBall', 'Quota']:
                seen_teams = set()
                for _, row in cat_df.iterrows():
                    # Handle Team grouping
                    p1 = str(row['Player'])
                    p2 = str(row['Partner']) if pd.notna(row['Partner']) and row['Partner'] else ""
                    team_key = tuple(sorted([p1, p2]))
                    if team_key not in seen_teams:
                        seen_teams.add(team_key)
                        names = f"{p1} & {p2}" if p2 else p1
                        results.append({'rank': row['Team_Rank'], 'names': names, 'amount': row['Amount']})
            else:
                # For individual games (NetMedal), rank by payout amount
                sorted_cat = cat_df.sort_values('Amount', ascending=False)
                current_rank = 1
                prev_amount = None
                rank_counter = 0

                for _, row in sorted_cat.iterrows():
                    rank_counter += 1
                    if prev_amount is not None and row['Amount'] < prev_amount:
                        current_rank = rank_counter

                    # Determine rank label
                    same_amount_count = (sorted_cat['Amount'] == row['Amount']).sum()
                    if same_amount_count > 1:
                        rank_label = f"T{current_rank}"
                    else:
                        rank_label = str(current_rank)

                    results.append({'rank': rank_label, 'names': row['Player'], 'amount': row['Amount']})
                    prev_amount = row['Amount']

            results.sort(key=lambda x: x['amount'], reverse=True)
            for res in results:
                rank_str = f"{res['rank']}: " if res['rank'] else ""
                html += f"<li class='m-0'>{rank_str}{res['names']} - ${res['amount']:.0f}</li>"
            html += "</ul></div>"

    html += "</div><div class='space-y-4'>" 
    for cat_key, cat_title in [('GrossSkins', 'Gross Skins'), ('NetSkins', 'Net Skins')]:
        cat_df = day_df[day_df['Category'] == cat_key]
        if not cat_df.empty:
            html += f"<div><h5 class='font-bold text-gray-900 mb-1 mt-0'>{cat_title}</h5><ul class='list-none pl-0 m-0 space-y-1'>"
            grouped_results = []
            for _, row in cat_df.iterrows():
                grouped_results.append({'name': row['Player'], 'amount': row['Amount']})
            grouped_results.sort(key=lambda x: x['amount'], reverse=True)
            for res in grouped_results:
                html += f"<li class='m-0'>{res['name']} - ${res['amount']:.0f}</li>"
            html += "</ul></div>"
            
    html += "</div></div>"
    html += f"<p class='text-xs text-gray-400 mt-6 mb-0 italic'>Latest Tournament: {date_str}</p>"
    return html

def generate_tournament_pages(financials_df, scores_df):
    """Generates individual HTML pages for each 2026 tournament."""
    if financials_df.empty: return []

    # Filter for 2026 dates only
    # Assuming Tournament Year logic: Nov/Dec of previous year counts.
    # But user said "2026 results log" and "each of the 2026 tournaments".
    # We'll use the 'Tournament_Year' logic.
    financials_df['Tournament_Year'] = financials_df['Date'].apply(lambda x: x.year + 1 if x.month >= 11 else x.year)
    df_2026 = financials_df[financials_df['Tournament_Year'] == 2026]

    generated_links = []

    unique_dates = sorted(df_2026['Date'].unique(), reverse=True)

    for date_val in unique_dates:
        date_str = pd.to_datetime(date_val).strftime('%Y-%m-%d')
        day_df = df_2026[df_2026['Date'] == date_val].copy()

        # Merge with scores to get Partner info
        scores_copy = scores_df.copy()
        scores_copy['Date'] = pd.to_datetime(scores_copy['Date'])
        day_scores = scores_copy[scores_copy['Date'] == date_val][['Date', 'Player', 'Partner']]
        day_df = day_df.merge(day_scores, on=['Date', 'Player'], how='left')

        # Determine Format
        cats = day_df['Category'].unique()
        format_name = get_format_name(date_val, cats)

        # Build Winners HTML
        winners_html = ""
        cat_map = {'BestBall': 'Best Ball', 'Quota': 'Team Quota', 'NetMedal': 'Net Medal', 'GrossSkins': 'Gross Skins', 'NetSkins': 'Net Skins'}

        # Order categories
        ordered_cats = [c for c in ['BestBall', 'Quota', 'NetMedal', 'GrossSkins', 'NetSkins'] if c in cats]

        for cat in ordered_cats:
            cat_df = day_df[day_df['Category'] == cat]
            if cat_df.empty: continue

            cat_title = get_category_title(date_val, cat, cat_map.get(cat, cat))
            winners_html += f"<div class='mb-6'><h4 class='font-bold text-gray-800 uppercase text-sm tracking-wide mb-2'>{cat_title}</h4><ul class='space-y-2'>"

            # Group winners - keep teams together for team games
            grouped = []
            if cat in ['BestBall', 'Quota']:
                # For team games, group by team (using Partner field)
                seen_teams = set()
                for _, row in cat_df.iterrows():
                    p1 = str(row['Player'])
                    p2 = str(row['Partner']) if pd.notna(row['Partner']) and row['Partner'] else ""
                    team_key = tuple(sorted([p1, p2]))
                    if team_key not in seen_teams:
                        seen_teams.add(team_key)
                        names = f"{p1} & {p2}" if p2 else p1
                        grouped.append({'names': names, 'amount': row['Amount']})
            else:
                # For individual games, group players with same amount
                for amt, grp in cat_df.groupby('Amount'):
                    names = " & ".join(sorted(grp['Player'].tolist()))
                    grouped.append({'names': names, 'amount': amt})

            grouped.sort(key=lambda x: x['amount'], reverse=True)

            for g in grouped:
                winners_html += f"<li class='flex justify-between items-center text-gray-700 bg-white p-3 rounded-lg border border-gray-100'><span class='font-medium'>{g['names']}</span><span class='font-bold text-green-600'>${g['amount']:.0f}</span></li>"
            winners_html += "</ul></div>"

        # Generate Content
        content = get_barstool_writeup(date_str, format_name, winners_html)
        
        # Create HTML File
        filename = f"results_{date_str}.html"
        full_path = os.path.join(WEBSITE_DIR, filename)
        
        page_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Results: {date_str}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;900&display=swap" rel="stylesheet">
</head>
<body class="bg-gray-100 font-sans antialiased text-gray-900">
    <header class="bg-white border-b border-gray-200 sticky top-0 z-50">
        <div class="container mx-auto px-6 py-4 flex justify-between items-center">
            <a href="index.html" class="flex items-center gap-2 text-gray-500 hover:text-green-600 transition">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18"></path></svg>
                Back to Home
            </a>
            <div class="font-black text-xl tracking-tight">SG@SG RESULTS</div>
        </div>
    </header>
    <main class="container mx-auto px-6 py-12 max-w-3xl">
        <div class="text-center mb-10">
            <h1 class="text-4xl md:text-5xl font-black mb-4">{format_name} Recap</h1>
            <p class="text-gray-500 font-medium">{date_str}</p>
        </div>
        {content}
    </main>
    <footer class="bg-white border-t border-gray-200 mt-12 py-8 text-center text-gray-400 text-sm">
        &copy; 2026 SG@SG.
    </footer>
</body>
</html>"""
        
        with open(full_path, 'w') as f:
            f.write(page_html)
            
        generated_links.append({'date': date_str, 'file': filename, 'format': format_name})
        print(f"✅ Generated {filename}")
        
    return generated_links

def inject_results_log(links):
    """Injects the list of links into index.html using marker comments."""
    filepath = os.path.join(WEBSITE_DIR, 'index.html')
    if not os.path.exists(filepath): return

    with open(filepath, 'r') as f: html = f.read()

    # Generate HTML list
    list_html = "\n"
    for link in links:
        list_html += f"""                    <a href="{link['file']}" class="block p-3 rounded-lg bg-gray-50 hover:bg-purple-50 hover:text-purple-700 transition flex items-center justify-between group">
                        <div class="flex items-center">
                            <span class="w-2 h-2 bg-purple-400 rounded-full mr-3 group-hover:scale-125 transition-transform"></span>
                            <span class="font-medium">{link['date']}</span>
                        </div>
                        <span class="text-xs text-gray-400 group-hover:text-purple-500">{link['format']}</span>
                    </a>
"""

    # Use marker comments for reliable replacement (immune to nested HTML)
    pattern = r'(<!-- RESULTS-LOG-START -->)(.*?)(<!-- RESULTS-LOG-END -->)'

    if re.search(pattern, html, flags=re.DOTALL):
        html = re.sub(pattern, r'\1' + list_html + r'                    \3', html, flags=re.DOTALL)
        with open(filepath, 'w') as f: f.write(html)
        print("✅ Updated Results Log in index.html")
    else:
        print("⚠️ Could not find RESULTS-LOG markers in index.html")

def update_index_html(writeup_html):
    filepath = os.path.join(WEBSITE_DIR, 'index.html')
    if not os.path.exists(filepath): return
    with open(filepath, 'r') as f: html = f.read()

    # Regex replace the prose div content
    pattern = r'(<div class="prose prose-green max-w-none text-gray-600 space-y-4">).*?(<p class=\'text-xs text-gray-400 mt-6 mb-0 italic\'>.*?</p>)'
    if re.search(pattern, html, flags=re.DOTALL):
        html = re.sub(pattern, r'\1' + writeup_html, html, flags=re.DOTALL)
    
    with open(filepath, 'w') as f: f.write(html)
    print("✅ Updated Latest Results in index.html")


def format_decimal(value, digits=1):
    if pd.isna(value):
        return ""
    return f"{float(value):.{digits}f}"


def format_currency(value):
    if pd.isna(value) or abs(float(value)) < 0.005:
        return ""
    return f"${float(value):.2f}"


def generate_data_audit_page(scores_df, financials_df, handicaps_df):
    categories = ['BestBall', 'Quota', 'NetMedal', 'GrossSkins', 'NetSkins']

    score_cols = ['Date', 'Player', 'Gross_Score', 'Differential']
    score_base = scores_df[score_cols].copy() if not scores_df.empty else pd.DataFrame(columns=score_cols)

    handicap_cols = ['Date', 'Player', 'Handicap_Index', 'Course_Handicap']
    handicap_base = handicaps_df[handicap_cols].copy() if not handicaps_df.empty else pd.DataFrame(columns=handicap_cols)

    if not financials_df.empty:
        financial_pivot = (
            financials_df
            .pivot_table(index=['Date', 'Player'], columns='Category', values='Amount', aggfunc='sum')
            .reset_index()
        )
        for category in categories:
            if category not in financial_pivot.columns:
                financial_pivot[category] = 0.0
        financial_pivot = financial_pivot[['Date', 'Player', *categories]]
    else:
        financial_pivot = pd.DataFrame(columns=['Date', 'Player', *categories])

    key_frames = [
        frame[['Date', 'Player']]
        for frame in (score_base, handicap_base, financial_pivot)
        if not frame.empty
    ]
    if key_frames:
        base = pd.concat(key_frames, ignore_index=True).drop_duplicates().reset_index(drop=True)
    else:
        base = pd.DataFrame(columns=['Date', 'Player'])

    base = base.merge(score_base, on=['Date', 'Player'], how='left')
    base = base.merge(handicap_base, on=['Date', 'Player'], how='left')
    base = base.merge(financial_pivot, on=['Date', 'Player'], how='left')

    for category in categories:
        if category not in base.columns:
            base[category] = 0.0
    base[categories] = base[categories].fillna(0.0)
    base['Total_Payout'] = base[categories].sum(axis=1)

    def build_note(row):
        notes = []
        if pd.isna(row.get('Gross_Score')) and row.get('Total_Payout', 0) > 0:
            notes.append('Payout-only row')
        if pd.notna(row.get('Gross_Score')) and pd.isna(row.get('Handicap_Index')):
            notes.append('Missing handicap snapshot')
        return '; '.join(notes)

    base['Review_Notes'] = base.apply(build_note, axis=1)
    base = base.sort_values(['Date', 'Player']).reset_index(drop=True)

    if base.empty:
        sections_html = """
        <div class="bg-white rounded-2xl border border-gray-200 p-8 text-center text-gray-500">
            No canonical tournament rows found.
        </div>
        """
        nav_html = ""
        total_dates = 0
        total_rows = 0
    else:
        unique_dates = sorted(base['Date'].dropna().unique(), reverse=True)
        total_dates = len(unique_dates)
        total_rows = len(base)

        nav_links = []
        section_blocks = []

        for date_value in unique_dates:
            date_rows = base[base['Date'] == date_value].copy().sort_values(['Player'])
            date_str = pd.to_datetime(date_value).strftime('%Y-%m-%d')
            section_id = f"audit-{date_str}"

            players_with_scores = int(date_rows['Gross_Score'].notna().sum())
            players_with_hcp = int(date_rows['Handicap_Index'].notna().sum())
            players_with_payouts = int((date_rows['Total_Payout'] > 0).sum())
            payout_only = int(((date_rows['Gross_Score'].isna()) & (date_rows['Total_Payout'] > 0)).sum())

            nav_links.append(
                f"<a href='#{section_id}' class='px-3 py-2 rounded-full bg-white border border-gray-200 text-sm text-gray-700 hover:border-green-500 hover:text-green-700 transition'>{date_str}</a>"
            )

            row_html = []
            for row in date_rows.to_dict('records'):
                player_value = str(row['Player'])
                gross_value = "" if pd.isna(row.get('Gross_Score')) else f"{float(row.get('Gross_Score')):.0f}"
                total_relative_value = "" if pd.isna(row.get('Gross_Score')) else str(int(round(float(row.get('Gross_Score')) - COURSE_PAR)))
                total_relative_display = ""
                if total_relative_value != "":
                    total_relative_int = int(total_relative_value)
                    total_relative_display = f"{total_relative_int:+d}" if total_relative_int != 0 else "0"
                diff_value = "" if pd.isna(row.get('Differential')) else f"{float(row.get('Differential')):.1f}"
                hi_value = "" if pd.isna(row.get('Handicap_Index')) else f"{float(row.get('Handicap_Index')):.1f}"
                course_hcp_value = "" if pd.isna(row.get('Course_Handicap')) else f"{float(row.get('Course_Handicap')):.1f}"
                best_ball_value = "" if pd.isna(row.get('BestBall')) or float(row.get('BestBall', 0.0)) == 0 else f"{float(row.get('BestBall', 0.0)):.2f}"
                quota_value = "" if pd.isna(row.get('Quota')) or float(row.get('Quota', 0.0)) == 0 else f"{float(row.get('Quota', 0.0)):.2f}"
                net_medal_value = "" if pd.isna(row.get('NetMedal')) or float(row.get('NetMedal', 0.0)) == 0 else f"{float(row.get('NetMedal', 0.0)):.2f}"
                gross_skins_value = "" if pd.isna(row.get('GrossSkins')) or float(row.get('GrossSkins', 0.0)) == 0 else f"{float(row.get('GrossSkins', 0.0)):.2f}"
                net_skins_value = "" if pd.isna(row.get('NetSkins')) or float(row.get('NetSkins', 0.0)) == 0 else f"{float(row.get('NetSkins', 0.0)):.2f}"
                total_payout_value = "" if pd.isna(row.get('Total_Payout')) or float(row.get('Total_Payout', 0.0)) == 0 else f"{float(row.get('Total_Payout', 0.0)):.2f}"
                notes_value = row.get('Review_Notes') or ""
                row_html.append(
                    """
                    <tr class="border-t border-gray-100 hover:bg-gray-50/70">
                        <td data-sort-value="{player_value}" class="px-4 py-3 text-sm font-medium text-gray-900 whitespace-nowrap">{player}</td>
                        <td data-sort-value="{gross_value}" class="px-4 py-3 text-sm text-gray-600 text-right">{gross}</td>
                        <td data-sort-value="{total_relative_value}" class="px-4 py-3 text-sm text-gray-600 text-right">{total_relative_display}</td>
                        <td data-sort-value="{diff_value}" class="px-4 py-3 text-sm text-gray-600 text-right">{diff}</td>
                        <td data-sort-value="{hi_value}" class="px-4 py-3 text-sm text-gray-600 text-right">{hi}</td>
                        <td data-sort-value="{course_hcp_value}" class="px-4 py-3 text-sm text-gray-600 text-right">{course_hcp}</td>
                        <td data-sort-value="{best_ball_value}" class="px-4 py-3 text-sm text-gray-600 text-right">{best_ball}</td>
                        <td data-sort-value="{quota_value}" class="px-4 py-3 text-sm text-gray-600 text-right">{quota}</td>
                        <td data-sort-value="{net_medal_value}" class="px-4 py-3 text-sm text-gray-600 text-right">{net_medal}</td>
                        <td data-sort-value="{gross_skins_value}" class="px-4 py-3 text-sm text-gray-600 text-right">{gross_skins}</td>
                        <td data-sort-value="{net_skins_value}" class="px-4 py-3 text-sm text-gray-600 text-right">{net_skins}</td>
                        <td data-sort-value="{total_payout_value}" class="px-4 py-3 text-sm font-semibold text-gray-900 text-right">{total_payout}</td>
                        <td data-sort-value="{notes_value}" class="px-4 py-3 text-sm text-gray-500 whitespace-nowrap">{notes}</td>
                    </tr>
                    """.format(
                        player=escape(str(row['Player'])),
                        player_value=escape(player_value.lower()),
                        gross=format_decimal(row.get('Gross_Score'), 0),
                        gross_value=escape(gross_value),
                        total_relative_value=escape(total_relative_value),
                        total_relative_display=escape(total_relative_display),
                        diff=format_decimal(row.get('Differential'), 1),
                        diff_value=escape(diff_value),
                        hi=format_decimal(row.get('Handicap_Index'), 1),
                        hi_value=escape(hi_value),
                        course_hcp=format_decimal(row.get('Course_Handicap'), 1),
                        course_hcp_value=escape(course_hcp_value),
                        best_ball=format_currency(row.get('BestBall', 0.0)),
                        best_ball_value=escape(best_ball_value),
                        quota=format_currency(row.get('Quota', 0.0)),
                        quota_value=escape(quota_value),
                        net_medal=format_currency(row.get('NetMedal', 0.0)),
                        net_medal_value=escape(net_medal_value),
                        gross_skins=format_currency(row.get('GrossSkins', 0.0)),
                        gross_skins_value=escape(gross_skins_value),
                        net_skins=format_currency(row.get('NetSkins', 0.0)),
                        net_skins_value=escape(net_skins_value),
                        total_payout=format_currency(row.get('Total_Payout', 0.0)),
                        total_payout_value=escape(total_payout_value),
                        notes=escape(notes_value),
                        notes_value=escape(notes_value.lower()),
                    )
                )

            section_blocks.append(
                """
                <section id="{section_id}" class="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
                    <div class="p-6 border-b border-gray-100 bg-gray-50">
                        <div class="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
                            <div>
                                <p class="text-sm font-semibold uppercase tracking-[0.18em] text-green-700">Tournament Audit</p>
                                <h2 class="text-2xl font-bold text-gray-900">{date_str}</h2>
                                <p class="mt-2 text-sm text-gray-500">Validate gross totals, handicap snapshots, and payout rows against Squabbit.</p>
                            </div>
                            <div class="flex flex-wrap gap-2 text-sm">
                                <span class="px-3 py-2 rounded-full bg-white border border-gray-200 text-gray-700">Scored players: {players_with_scores}</span>
                                <span class="px-3 py-2 rounded-full bg-white border border-gray-200 text-gray-700">Handicap rows: {players_with_hcp}</span>
                                <span class="px-3 py-2 rounded-full bg-white border border-gray-200 text-gray-700">Payout rows: {players_with_payouts}</span>
                                <span class="px-3 py-2 rounded-full bg-white border border-gray-200 text-gray-700">Payout-only: {payout_only}</span>
                            </div>
                        </div>
                    </div>
                    <div class="overflow-x-auto">
                        <table class="min-w-full border-collapse" data-sort-table>
                            <thead class="bg-white">
                                <tr class="text-xs uppercase tracking-wide text-gray-500">
                                    <th class="px-4 py-3 text-left"><button type="button" class="w-full flex items-center gap-2 text-left hover:text-green-700 transition" data-sort-button data-sort-type="text"><span>Player</span><span class="text-[10px] text-gray-400" data-sort-indicator>&#8597;</span></button></th>
                                    <th class="px-4 py-3 text-right"><button type="button" class="w-full flex items-center justify-end gap-2 text-right hover:text-green-700 transition" data-sort-button data-sort-type="number"><span>Gross</span><span class="text-[10px] text-gray-400" data-sort-indicator>&#8597;</span></button></th>
                                    <th class="px-4 py-3 text-right"><button type="button" class="w-full flex items-center justify-end gap-2 text-right hover:text-green-700 transition" data-sort-button data-sort-type="number"><span>Total</span><span class="text-[10px] text-gray-400" data-sort-indicator>&#8597;</span></button></th>
                                    <th class="px-4 py-3 text-right"><button type="button" class="w-full flex items-center justify-end gap-2 text-right hover:text-green-700 transition" data-sort-button data-sort-type="number"><span>Diff</span><span class="text-[10px] text-gray-400" data-sort-indicator>&#8597;</span></button></th>
                                    <th class="px-4 py-3 text-right"><button type="button" class="w-full flex items-center justify-end gap-2 text-right hover:text-green-700 transition" data-sort-button data-sort-type="number"><span>HI</span><span class="text-[10px] text-gray-400" data-sort-indicator>&#8597;</span></button></th>
                                    <th class="px-4 py-3 text-right"><button type="button" class="w-full flex items-center justify-end gap-2 text-right hover:text-green-700 transition" data-sort-button data-sort-type="number"><span>Course HCP</span><span class="text-[10px] text-gray-400" data-sort-indicator>&#8597;</span></button></th>
                                    <th class="px-4 py-3 text-right"><button type="button" class="w-full flex items-center justify-end gap-2 text-right hover:text-green-700 transition" data-sort-button data-sort-type="number"><span>Best Ball</span><span class="text-[10px] text-gray-400" data-sort-indicator>&#8597;</span></button></th>
                                    <th class="px-4 py-3 text-right"><button type="button" class="w-full flex items-center justify-end gap-2 text-right hover:text-green-700 transition" data-sort-button data-sort-type="number"><span>Quota</span><span class="text-[10px] text-gray-400" data-sort-indicator>&#8597;</span></button></th>
                                    <th class="px-4 py-3 text-right"><button type="button" class="w-full flex items-center justify-end gap-2 text-right hover:text-green-700 transition" data-sort-button data-sort-type="number"><span>Net Medal</span><span class="text-[10px] text-gray-400" data-sort-indicator>&#8597;</span></button></th>
                                    <th class="px-4 py-3 text-right"><button type="button" class="w-full flex items-center justify-end gap-2 text-right hover:text-green-700 transition" data-sort-button data-sort-type="number"><span>Gross Skins</span><span class="text-[10px] text-gray-400" data-sort-indicator>&#8597;</span></button></th>
                                    <th class="px-4 py-3 text-right"><button type="button" class="w-full flex items-center justify-end gap-2 text-right hover:text-green-700 transition" data-sort-button data-sort-type="number"><span>Net Skins</span><span class="text-[10px] text-gray-400" data-sort-indicator>&#8597;</span></button></th>
                                    <th class="px-4 py-3 text-right"><button type="button" class="w-full flex items-center justify-end gap-2 text-right hover:text-green-700 transition" data-sort-button data-sort-type="number"><span>Total Payout</span><span class="text-[10px] text-gray-400" data-sort-indicator>&#8597;</span></button></th>
                                    <th class="px-4 py-3 text-left"><button type="button" class="w-full flex items-center gap-2 text-left hover:text-green-700 transition" data-sort-button data-sort-type="text"><span>Notes</span><span class="text-[10px] text-gray-400" data-sort-indicator>&#8597;</span></button></th>
                                </tr>
                            </thead>
                            <tbody>
                                {rows}
                            </tbody>
                        </table>
                    </div>
                </section>
                """.format(
                    section_id=section_id,
                    date_str=date_str,
                    players_with_scores=players_with_scores,
                    players_with_hcp=players_with_hcp,
                    players_with_payouts=players_with_payouts,
                    payout_only=payout_only,
                    rows="".join(row_html),
                )
            )

        nav_html = "".join(nav_links)
        sections_html = "\n".join(section_blocks)

    page_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SG@SG Data Audit</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-stone-50 text-gray-900 font-sans antialiased">
    <header class="bg-white border-b border-gray-200 sticky top-0 z-40">
        <div class="container mx-auto px-6 py-4 flex items-center justify-between gap-4">
            <div>
                <p class="text-xs uppercase tracking-[0.22em] text-green-700 font-semibold">Operator View</p>
                <h1 class="text-2xl font-bold text-gray-900">Data Audit</h1>
            </div>
            <a href="index.html" class="text-sm text-gray-500 hover:text-green-700 transition">Back to Home</a>
        </div>
    </header>

    <main class="container mx-auto px-6 py-10 space-y-8">
        <section class="bg-white rounded-2xl border border-gray-200 shadow-sm p-8">
            <div class="max-w-4xl">
                <h2 class="text-3xl font-bold text-gray-900 mb-3">Canonical review report for manual Squabbit validation</h2>
                <p class="text-gray-600 leading-7">
                    This page is intentionally narrow: one row per player per tournament date, showing the fields most worth checking manually.
                    Use it to validate gross totals, handicap snapshots, payouts by game, and payout-only exceptions before or after processing.
                </p>
            </div>
            <div class="mt-6 rounded-2xl border border-emerald-200 bg-emerald-50/70 p-6">
                <h3 class="text-lg font-bold text-gray-900">How To Audit After Each Tournament Load</h3>
                <p class="mt-2 text-sm text-gray-600">
                    After each processed tournament date, run these three Squabbit checks and compare them to this page.
                </p>
                <ol class="mt-4 space-y-3 text-sm text-gray-700 list-decimal pl-5">
                    <li>
                        In Squabbit, open <span class="font-semibold">Leaderboard</span>, click <span class="font-semibold">Games</span>, sort <span class="font-semibold">Total Winnings</span> highest to lowest, and verify <span class="font-semibold">Total Payout</span> by player.
                    </li>
                    <li>
                        In Squabbit, click the <span class="font-semibold">Gross</span> tab, sort by the <span class="font-semibold">Total</span> column, and verify <span class="font-semibold">Gross</span> and <span class="font-semibold">Total</span> by player.
                    </li>
                    <li>
                        In Squabbit, click the top-right <span class="font-semibold">gear icon</span>, open <span class="font-semibold">Players</span>, sort the <span class="font-semibold">HDCP</span> column descending, then sort <span class="font-semibold">HI</span> on this page and verify handicap index values.
                    </li>
                </ol>
            </div>
            <div class="mt-6 grid gap-4 md:grid-cols-3">
                <div class="rounded-2xl border border-gray-200 bg-gray-50 p-5">
                    <p class="text-sm text-gray-500">Tournament dates</p>
                    <p class="mt-1 text-3xl font-bold text-gray-900">{total_dates}</p>
                </div>
                <div class="rounded-2xl border border-gray-200 bg-gray-50 p-5">
                    <p class="text-sm text-gray-500">Player-date rows</p>
                    <p class="mt-1 text-3xl font-bold text-gray-900">{total_rows}</p>
                </div>
                <div class="rounded-2xl border border-gray-200 bg-gray-50 p-5">
                    <p class="text-sm text-gray-500">Included review fields</p>
                    <p class="mt-1 text-sm font-medium text-gray-700">Gross, Total, Differential, HI, Course HCP, Best Ball, Quota, Net Medal, Gross Skins, Net Skins, Total Payout</p>
                </div>
            </div>
        </section>

        <section class="bg-white rounded-2xl border border-gray-200 shadow-sm p-6">
            <div class="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                <div>
                    <h2 class="text-lg font-bold text-gray-900">Jump to tournament date</h2>
                    <p class="text-sm text-gray-500">The newest dates are listed first.</p>
                </div>
                <div class="flex flex-wrap gap-2">
                    {nav_html}
                </div>
            </div>
        </section>

        {sections_html}
    </main>

    <footer class="bg-white border-t border-gray-200 mt-12">
        <div class="container mx-auto px-6 py-6 text-center text-sm text-gray-400">
            &copy; 2026 SG@SG. Data audit view generated from canonical CSVs.
        </div>
    </footer>
    <script>
        document.querySelectorAll('[data-sort-table]').forEach((table) => {{
            const tbody = table.querySelector('tbody');
            const buttons = Array.from(table.querySelectorAll('[data-sort-button]'));

            const compareValues = (leftValue, rightValue, sortType, direction) => {{
                const leftBlank = leftValue === '';
                const rightBlank = rightValue === '';

                if (leftBlank && rightBlank) return 0;
                if (leftBlank) return 1;
                if (rightBlank) return -1;

                let comparison = 0;
                if (sortType === 'number') {{
                    comparison = parseFloat(leftValue) - parseFloat(rightValue);
                }} else {{
                    comparison = leftValue.localeCompare(rightValue, undefined, {{ numeric: true, sensitivity: 'base' }});
                }}

                return direction === 'asc' ? comparison : -comparison;
            }};

            buttons.forEach((button, columnIndex) => {{
                button.addEventListener('click', () => {{
                    const nextDirection = button.dataset.sortDirection === 'asc' ? 'desc' : 'asc';
                    const sortType = button.dataset.sortType || 'text';
                    const rows = Array.from(tbody.querySelectorAll('tr'));

                    buttons.forEach((otherButton) => {{
                        if (otherButton !== button) {{
                            otherButton.dataset.sortDirection = '';
                            otherButton.setAttribute('aria-sort', 'none');
                            const indicator = otherButton.querySelector('[data-sort-indicator]');
                            if (indicator) indicator.innerHTML = '&#8597;';
                        }}
                    }});

                    rows.sort((leftRow, rightRow) => {{
                        const leftCell = leftRow.children[columnIndex];
                        const rightCell = rightRow.children[columnIndex];
                        const leftValue = (leftCell.dataset.sortValue || leftCell.textContent || '').trim();
                        const rightValue = (rightCell.dataset.sortValue || rightCell.textContent || '').trim();
                        return compareValues(leftValue, rightValue, sortType, nextDirection);
                    }});

                    rows.forEach((row) => tbody.appendChild(row));
                    button.dataset.sortDirection = nextDirection;
                    button.setAttribute('aria-sort', nextDirection === 'asc' ? 'ascending' : 'descending');
                    const indicator = button.querySelector('[data-sort-indicator]');
                    if (indicator) indicator.innerHTML = nextDirection === 'asc' ? '&#8593;' : '&#8595;';
                }});
            }});
        }});
    </script>
</body>
</html>"""

    output_path = os.path.join(WEBSITE_DIR, "DataAudit.html")
    with open(output_path, 'w') as output_file:
        output_file.write(page_html)
    print("✅ Updated DataAudit.html")


def run_auxiliary_script(script_name):
    script_path = os.path.join(SCRIPT_DIR, script_name)
    print(f"🔄 Refreshing {script_name}...")
    subprocess.run([sys.executable, script_path], cwd=PROJECT_ROOT, check=True)


def run_pipeline():
    print("--- ⛳ Starting CSV-Based Site Refresh ---")
    
    # 1. Load Data
    if not os.path.exists(SCORES_FILE):
        print("❌ Critical: scores.csv not found.")
        return False

    scores = pd.read_csv(SCORES_FILE, parse_dates=['Date'])
    financials = pd.read_csv(FINANCIALS_FILE, parse_dates=['Date']) if os.path.exists(FINANCIALS_FILE) else pd.DataFrame()
    handicaps = pd.read_csv(HANDICAPS_FILE, parse_dates=['Date']) if os.path.exists(HANDICAPS_FILE) else pd.DataFrame()
    course = pd.read_csv(COURSE_FILE) if os.path.exists(COURSE_FILE) else pd.DataFrame()

    scores = ensure_scores_columns(scores)
    if not handicaps.empty:
        handicaps = ensure_handicap_columns(handicaps)
    
    # Normalize Course Info
    if not course.empty:
        course.columns = [c.strip().lower() for c in course.columns]
        course['hole'] = pd.to_numeric(course['hole'].astype(str).str.replace('H', ''), errors='coerce')
    
    # Filter 13 Months for Handicap Analysis
    cutoff_date = datetime.now() - pd.DateOffset(months=MONTHS_LOOKBACK)
    
    # 2. Prepare Base Dataframe (Scores + Financials Aggregated)
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
    base = scores.copy()
    if not handicaps.empty:
        base = base.merge(
            handicaps[['Date', 'Player', 'Handicap_Index', 'Course_Handicap']],
            on=['Date', 'Player'],
            how='left',
        )
    if not fin_agg.empty:
        base = base.merge(fin_agg, on=['Date', 'Player'], how='left')

    # Fill missing money with 0
    money_cols = ['BB_Earn', 'Quota_Earn', 'net_medal_earnings', 'Gskins_earnings', 'Nskins_earnings']
    for c in money_cols:
        if c not in base.columns: base[c] = 0.0
    fill_map = {col: 0.0 for col in money_cols}
    base = base.fillna(fill_map)
    base['Total_Earnings'] = base[money_cols].sum(axis=1)
    if 'Course_Handicap' in base.columns:
        base['Course_Handicap_Used'] = base['Course_Handicap']
    else:
        base['Course_Handicap_Used'] = pd.NA

    base['Tournament_Year'] = base['Date'].apply(lambda x: x.year + 1 if x.month >= 11 else x.year)

    # 3. Handicap Analysis (Best 3/6)
    analysis_data_best3 = []
    analysis_data_best6 = []
    analysis_data_last2 = []
    analysis_base = base[base['Date'] >= cutoff_date].copy()

    for player, group in analysis_base.groupby('Player'):
        if group['Course_Handicap_Used'].dropna().empty:
            continue
        rounds = len(group)
        if rounds < 1: continue

        # Latest course handicap snapshot
        latest_row = group[group['Course_Handicap_Used'].notna()].sort_values('Date', ascending=False).iloc[0]
        current_hcp = float(latest_row['Course_Handicap_Used']) if pd.notna(latest_row['Course_Handicap_Used']) else 0.0
        
        diffs = group['Differential'].dropna().tolist()
        gross_scores = group['Gross_Score'].tolist()
        
        # Sort by Date descending for Last 2
        group_sorted = group.sort_values('Date', ascending=False)
        last2_diffs = group_sorted['Differential'].head(2).tolist()
        
        avg_gross = sum(gross_scores) / len(gross_scores)
        avg_net = (group['Gross_Score'] - group['Course_Handicap_Used']).dropna().mean()
        if pd.isna(avg_net):
            avg_net = 0.0

        # Best 3
        best3_diffs = sorted(diffs)[:3]
        implied_3 = sum(best3_diffs) / len(best3_diffs) if best3_diffs else 0
        adj_3 = implied_3 - current_hcp

        # Best 6
        best6_diffs = sorted(diffs)[:6]
        implied_6 = sum(best6_diffs) / len(best6_diffs) if best6_diffs else 0
        adj_6 = implied_6 - current_hcp
        
        # Last 2 (Trend)
        implied_2 = sum(last2_diffs) / len(last2_diffs) if last2_diffs else 0
        adj_2 = implied_2 - current_hcp

        common = {
            'name': player, 'current': round(current_hcp, 1),
            'avgGross': round(avg_gross, 1), 'avgNet': round(avg_net, 1),
            'rounds': rounds, 'notes': ''
        }
        analysis_data_best3.append({**common, 'implied': round(implied_3, 1), 'adjustment': round(adj_3, 1)})
        analysis_data_best6.append({**common, 'implied': round(implied_6, 1), 'adjustment': round(adj_6, 1)})
        analysis_data_last2.append({**common, 'implied': round(implied_2, 1), 'adjustment': round(adj_2, 1)})
    
    inject_to_html("HandicapAnalysis.html", "dataBest3", analysis_data_best3, is_json=True)
    inject_to_html("HandicapAnalysis.html", "dataBest6", analysis_data_best6, is_json=True)
    inject_to_html("HandicapAnalysis.html", "dataLast2", analysis_data_last2, is_json=True)

    # 4. Handicap Detail (Drilldown)
    detail_lines = ["Player\tDate\tGross Score\tCourse HCP Used\tNet Score\tRound Differential\tTotal_Rounds_Available\tNotes"]
    rounds_map = base.groupby('Player').size().to_dict()
    
    for _, row in base.sort_values(['Player', 'Date'], ascending=[True, False]).iterrows():
        d_str = row['Date'].strftime('%Y-%m-%d')
        hcp = row.get('Course_Handicap_Used', pd.NA)
        gross = row['Gross_Score']
        net = gross - hcp if pd.notna(hcp) else pd.NA
        diff = row['Differential']
        r_count = rounds_map.get(row['Player'], 0)
        note = "" if pd.notna(hcp) else "Missing handicap snapshot"
        hcp_display = f"{hcp:.1f}" if pd.notna(hcp) else ""
        net_display = f"{net:.1f}" if pd.notna(net) else ""
        detail_lines.append(f"{row['Player']}\t{d_str}\t{gross}\t{hcp_display}\t{net_display}\t{diff:.1f}\t{r_count}\t{note}")
    
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
        
        cols_out = ['Player', 'BB_Earn', 'Quota_Earn', 'Nskins_earnings', 'Gskins_earnings', 'net_medal_earnings', 'Total_Earnings']
        headers = ['Name', 'Best_Ball_Earnings', 'Quota_Earnings', 'Net_Skins_Earnings', 'Gross_Skins_Earnings', 'Net_Earnings', 'Total Earnings']
        
        if year == 2025:
             df_out = df_year[['Player', 'BB_Earn', 'Nskins_earnings', 'Gskins_earnings', 'net_medal_earnings', 'Total_Earnings']]
             df_out.columns = ['Name', 'Best_Ball_Earnings', 'Net_Skins_Earnings', 'Gross_Skins_Earnings', 'Net_Earnings', 'Total Earnings']
        else:
             df_out = df_year[cols_out]
             df_out.columns = headers
             
        inject_to_html(f"MoneyList{year}.html", "csvData", df_out.to_csv(index=False))

    # 6. Hole Averages
    score_cols = [f'H{i}' for i in range(1, 19)]
    melted = scores.melt(id_vars=['Player', 'Date'], value_vars=score_cols, var_name='hole', value_name='score')
    melted['hole'] = pd.to_numeric(melted['hole'].str.replace('H', ''), errors='coerce')
    
    hole_avg = melted.groupby('hole')['score'].mean().round(2).reset_index()
    if not course.empty:
        hole_avg = hole_avg.merge(course[['hole', 'par']], on='hole', how='left')
    hole_avg['par'] = hole_avg['par'].fillna(4).astype(int)
    
    inject_to_html("AverageScore.html", "holeData", hole_avg[['hole', 'score', 'par']].to_dict('records'), is_json=True)

    # 7. Hole Index
    sg_index_map = {1: 5, 2: 15, 3: 13, 4: 7, 5: 1, 6: 17, 7: 9, 8: 3, 9: 11, 
                    10: 12, 11: 14, 12: 2, 13: 16, 14: 10, 15: 6, 16: 18, 17: 8, 18: 4}
    
    idx_df = hole_avg.copy()
    idx_df['diff'] = idx_df['score'] - idx_df['par']
    idx_df = idx_df.sort_values('diff', ascending=False)
    idx_df['rank'] = range(1, 19)
    
    hole_index_data = [{"hole": int(r['hole']), "x": sg_index_map.get(r['hole'], 0), "y": int(r['rank'])} for _, r in idx_df.iterrows()]
    inject_to_html("HoleIndex.html", "rawData", hole_index_data, is_json=True)

    # 8. Player Stats
    stats_df = base.copy()
    stats_df['Net_Score'] = stats_df['Gross_Score'] - stats_df['Course_Handicap_Used']
    stats_df['Net_to_Par'] = stats_df['Net_Score'] - 72
    
    p_stats = stats_df.groupby('Player').agg({
        'Gross_Score': 'mean', 'Net_Score': 'mean', 'Net_to_Par': 'mean'
    }).round(2).reset_index()
    p_stats.columns = ['Player', 'Gross_Score', 'net_score', 'Net_to_Par']
    inject_to_html("PlayerStats.html", "playerStatsData", p_stats.to_csv(index=False))

    # 9. Latest Results Writeup
    writeup = get_latest_results_writeup(financials, scores)
    if writeup:
        update_index_html(writeup)

    # 10. Generate Tournament Pages & Update Log
    links = generate_tournament_pages(financials, scores)
    if links:
        inject_results_log(links)

    # 11. Operator Data Audit
    generate_data_audit_page(scores, financials, handicaps)

    run_auxiliary_script("generate_methodology_data.py")
    run_auxiliary_script("convert_json_to_js.py")
    return True

def get_repo_changes():
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    changes = []
    for line in result.stdout.splitlines():
        if not line:
            continue
        status = line[:2]
        path = line[3:]
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        changes.append((status, path))
    return changes


def enforce_publish_scope():
    changes = get_repo_changes()
    unexpected = [
        path for _, path in changes
        if not any(path == allowed or path.startswith(f"{allowed}/") for allowed in PUBLISH_PATHS)
    ]
    if unexpected:
        print("❌ Refusing to publish with unrelated repo changes present:")
        for path in unexpected:
            print(f"   - {path}")
        print("\nClean, ignore, or commit those files separately and retry publish.")
        return False
    return True


def sync():
    print("🚀 Pushing Updates...")
    if not enforce_publish_scope():
        return False
    subprocess.run(["git", "add", "--", *PUBLISH_PATHS], cwd=PROJECT_ROOT, check=True)
    subprocess.run(
        ["git", "commit", "-m", f"Automated Update {datetime.now().strftime('%Y-%m-%d')}"],
        cwd=PROJECT_ROOT,
        check=True,
    )
    subprocess.run(["git", "push"], cwd=PROJECT_ROOT, check=True)
    print("🎉 Done.")
    return True

def main():
    parser = argparse.ArgumentParser(description="Regenerate website pages from CSV data.")
    parser.add_argument(
        "--publish",
        action="store_true",
        help="Stage, commit, and push generated changes after a successful build",
    )
    args = parser.parse_args()

    success = run_pipeline()
    if not success:
        sys.exit(1)
    if args.publish:
        if not sync():
            sys.exit(1)
    else:
        print("ℹ️ Local build complete. Publish skipped.")

if __name__ == "__main__":
    main()
