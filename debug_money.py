import pandas as pd
import os
from datetime import datetime

DATA_DIR = "data"
SCORES_FILE = os.path.join(DATA_DIR, "scores.csv")
FINANCIALS_FILE = os.path.join(DATA_DIR, "financials.csv")

def debug():
    print("--- DEBUGGING MONEY LIST ---")
    
    # 1. Load
    scores = pd.read_csv(SCORES_FILE, parse_dates=['Date'])
    financials = pd.read_csv(FINANCIALS_FILE, parse_dates=['Date'])
    
    print(f"Scores Rows: {len(scores)}")
    print(f"Financials Rows: {len(financials)}")
    
    # Check for Chris Beck on 2024-11-23
    print("\n--- Check: Chris Beck / 2024-11-23 ---")
    s_check = scores[(scores['Date'] == '2024-11-23') & (scores['Player'] == 'Chris Beck')]
    f_check = financials[(financials['Date'] == '2024-11-23') & (financials['Player'] == 'Chris Beck')]
    print("Score Entry:", "Found" if not s_check.empty else "MISSING")
    print("Fin Entry:", "Found" if not f_check.empty else "MISSING")
    if not f_check.empty:
        print(f_check)

    # 2. Pivot
    fin_pivot = financials.pivot_table(index=['Date', 'Player'], columns='Category', values='Amount', aggfunc='sum').reset_index().fillna(0)
    col_map = {
        'BestBall': 'BB_Earn', 'Quota': 'Quota_Earn', 
        'NetMedal': 'net_medal_earnings', 
        'GrossSkins': 'Gskins_earnings', 'NetSkins': 'Nskins_earnings'
    }
    fin_pivot = fin_pivot.rename(columns=col_map)
    print(f"\nPivoted Financials Rows: {len(fin_pivot)}")
    print("Columns in Pivot:", fin_pivot.columns.tolist())
    
    # 3. Merge
    base = scores.copy()
    base = base.merge(fin_pivot, on=['Date', 'Player'], how='left')
    
    # Check merge result for Chris Beck
    b_check = base[(base['Date'] == '2024-11-23') & (base['Player'] == 'Chris Beck')]
    print("\nMerged Base Entry (Chris Beck):")
    print(b_check[['Date', 'Player', 'BB_Earn']] if 'BB_Earn' in b_check.columns else "BB_Earn Missing")

    # 4. Fill NaNs
    money_cols = ['BB_Earn', 'Quota_Earn', 'net_medal_earnings', 'Gskins_earnings', 'Nskins_earnings']
    for c in money_cols:
        if c not in base.columns: base[c] = 0.0
    base = base.fillna(0)
    base['Total_Earnings'] = base[money_cols].sum(axis=1)
    
    # 5. Year
    base['Tournament_Year'] = base['Date'].apply(lambda x: x.year + 1 if x.month >= 11 else x.year)
    
    print("\n--- Year Summary ---")
    print(base.groupby('Tournament_Year')['Total_Earnings'].sum())
    
    # 6. Check 2026 List
    df_2026 = base[base['Tournament_Year'] == 2026]
    
    # 7. Generate Debug HTML
    print("\n--- Generating Debug HTML ---")
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <body>
        <h1>Debug Money List</h1>
        <table border="1" id="moneyTable">
            <thead>
                <tr>
                    <th>Player</th>
                    <th>Total Earnings</th>
                </tr>
            </thead>
            <tbody id="tableBody"></tbody>
        </table>
        <script>
            const csvData = `{df_2026.groupby('Player')['Total_Earnings'].sum().reset_index().to_csv(index=False)}`;
            console.log("Raw CSV:", csvData);
            
            const rows = csvData.trim().split('\\n').slice(1);
            const tbody = document.getElementById('tableBody');
            
            rows.forEach(row => {{
                const cols = row.split(',');
                const tr = document.createElement('tr');
                cols.forEach(col => {{
                    const td = document.createElement('td');
                    td.textContent = col;
                    tr.appendChild(td);
                }});
                tbody.appendChild(tr);
            }});
        </script>
    </body>
    </html>
    """
    with open("website/debug_money.html", "w") as f:
        f.write(html_content)
    print("Created website/debug_money.html")

if __name__ == "__main__":
    debug()
