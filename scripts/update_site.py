import pandas as pd
import os
import json
import re
import subprocess
import random
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

def get_barstool_writeup(date_str, format_name, winners_html):
    opener = random.choice(OPENERS)
    middler = random.choice(MIDDLERS)
    closer = random.choice(CLOSERS)
    
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
    for cat_key, cat_title in cat_map.items():
        cat_df = day_df[day_df['Category'] == cat_key]
        if not cat_df.empty:
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
                for _, row in cat_df.iterrows():
                    results.append({'rank': row['Individual_Rank'], 'names': row['Player'], 'amount': row['Amount']})
            
            results.sort(key=lambda x: x['amount'], reverse=True)
            for res in results:
                rank_str = f"{res['rank']}: " if pd.notna(res['rank']) and res['rank'] else ""
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
    html += f"<p class='text-xs text-gray-400 mt-6 mb-0 italic'>Run Date: {datetime.now().strftime('%Y-%m-%d')}</p>"
    return html

def generate_tournament_pages(financials_df):
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
        day_df = df_2026[df_2026['Date'] == date_val]
        
        # Determine Format
        cats = day_df['Category'].unique()
        format_name = "Tournament"
        if 'Quota' in cats: format_name = "Team Quota"
        elif 'BestBall' in cats: format_name = "Best Ball"
        elif 'NetMedal' in cats: format_name = "Net Medal"
        
        # Build Winners HTML
        winners_html = ""
        cat_map = {'BestBall': 'Best Ball', 'Quota': 'Team Quota', 'NetMedal': 'Net Medal', 'GrossSkins': 'Gross Skins', 'NetSkins': 'Net Skins'}
        
        # Order categories
        ordered_cats = [c for c in ['BestBall', 'Quota', 'NetMedal', 'GrossSkins', 'NetSkins'] if c in cats]
        
        for cat in ordered_cats:
            cat_df = day_df[day_df['Category'] == cat]
            if cat_df.empty: continue
            
            winners_html += f"<div class='mb-6'><h4 class='font-bold text-gray-800 uppercase text-sm tracking-wide mb-2'>{cat_map.get(cat, cat)}</h4><ul class='space-y-2'>"
            
            # Group winners
            grouped = []
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
    pattern = r'(<div class="prose prose-green max-w-none text-gray-600 space-y-4">).*?(<p class=\'text-xs text-gray-400 mt-6 mb-0 italic\'>Run Date: .*?</p>)'
    if re.search(pattern, html, flags=re.DOTALL):
        html = re.sub(pattern, r'\1' + writeup_html, html, flags=re.DOTALL)
    
    with open(filepath, 'w') as f: f.write(html)
    print("✅ Updated Latest Results in index.html")

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
    base['Differential'] = (base['Gross_Score'] - COURSE_RATING) * 113 / SLOPE_RATING
    base['Differential'] = base['Differential'].round(1)
    
    analysis_data_best3 = []
    analysis_data_best6 = []
    analysis_data_last2 = []
    analysis_base = base[base['Date'] >= cutoff_date].copy()

    for player, group in analysis_base.groupby('Player'):
        rounds = len(group)
        if rounds < 1: continue

        # Latest Handicap
        latest_row = group.sort_values('Date', ascending=False).iloc[0]
        current_hcp = float(latest_row['Round_Handicap']) if 'Round_Handicap' in latest_row else 0.0
        
        diffs = group['Differential'].dropna().tolist()
        gross_scores = group['Gross_Score'].tolist()
        
        # Sort by Date descending for Last 2
        group_sorted = group.sort_values('Date', ascending=False)
        last2_diffs = group_sorted['Differential'].head(2).tolist()
        
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
    detail_lines = ["Player\tDate\tGross Score\tHCP Used\tNet Score\tRound Differential\tTotal_Rounds_Available\tNotes"]
    rounds_map = base.groupby('Player').size().to_dict()
    
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
    stats_df['Net_Score'] = stats_df['Gross_Score'] - stats_df['Round_Handicap']
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
    links = generate_tournament_pages(financials)
    if links:
        inject_results_log(links)

def sync():
    print("🚀 Pushing Updates...")
    subprocess.run(["git", "add", "."], cwd=PROJECT_ROOT)
    subprocess.run(["git", "commit", "-m", f"Automated Update {datetime.now().strftime('%Y-%m-%d')}"], cwd=PROJECT_ROOT)
    subprocess.run(["git", "push"], cwd=PROJECT_ROOT)
    print("🎉 Done.")

if __name__ == "__main__":
    run_pipeline()
    sync()
