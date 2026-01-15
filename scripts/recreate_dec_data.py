import pandas as pd
import os
from datetime import datetime

# Define Data
TOURNAMENT_DATE = "2025-12-20"

# --- 1. SCORES & HANDICAPS ---
# Format: Name, Hcp, H1..H9, H10..H18
raw_data = [
    ("Jeff De Laveaga", 0.5, [4,3,3,5,3,5,4,4,5], [3,5,3,4,4,4,3,4,4]),
    ("Neil Harris", -1.7, [4,4,3,4,4,4,4,5,6], [4,5,3,3,4,4,3,4,5]),
    ("Eric Weiss", 1.0, [4,4,3,4,5,4,3,4,5], [4,5,4,4,4,5,5,4,5]),
    ("Todd Densley", -0.8, [4,4,2,6,4,4,3,3,5], [4,5,5,3,5,4,4,4,7]),
    ("Rick Meewes", 6.5, [4,5,3,4,6,5,3,5,6], [4,5,4,2,3,4,4,4,6]),
    ("Ben Magnone", 10.4, [4,4,3,5,3,5,4,5,6], [4,6,4,4,4,4,3,5,5]),
    ("Derek Becko", 3.5, [6,3,3,5,4,5,4,4,5], [4,5,4,3,4,4,4,5,7]),
    ("Joe Sepessy", 6.1, [5,4,3,5,4,4,3,4,6], [4,6,5,4,4,5,4,4,5]),
    ("Justin Deuker", 3.0, [5,5,3,5,4,3,3,5,6], [4,6,4,3,4,4,4,4,7]),
    ("Kiernan Mattson", 1.4, [5,4,4,6,6,4,3,4,6], [3,4,5,3,4,5,4,4,5]),
    ("Ron Marino", 7.2, [4,5,4,5,4,3,3,4,4], [5,5,5,3,5,4,5,4,7]),
    ("Travis Ingram", 6.6, [3,5,4,6,4,5,3,4,5], [4,6,6,3,5,4,3,2,7]),
    ("Clark Koch", 8.8, [5,5,3,5,6,4,3,4,5], [5,5,5,4,4,5,4,4,4]),
    ("Paul Benga", 4.2, [4,4,3,5,4,5,3,4,5], [5,6,5,6,4,4,4,4,5]),
    ("Dan Denham", 6.5, [5,6,4,5,4,4,3,3,6], [4,5,5,3,5,5,4,4,6]),
    ("Dusty Wasmund", 7.6, [7,4,2,5,5,4,4,6,4], [5,5,5,3,5,4,4,5,5]),
    ("David Pearson", 9.6, [6,4,3,6,5,5,3,4,5], [5,6,5,3,5,5,4,3,6]),
    ("Kevin Barber", 15.3, [6,4,2,5,5,4,4,5,5], [5,6,6,3,4,5,5,3,7]),
    ("Steve Mccormick", 9.2, [5,5,3,5,5,4,3,5,5], [5,5,5,4,4,5,5,4,7]),
    ("Steve Rosenbluth", 8.4, [4,4,4,6,5,4,3,6,6], [4,6,5,4,5,4,4,4,6]),
    ("Christopher Royce", 13.9, [4,5,3,4,4,5,3,4,6], [5,4,7,5,7,4,5,4,6]),
    ("Rich Mckeon", 11.0, [4,4,3,6,4,5,4,4,5], [5,6,4,6,5,5,5,4,7]),
    ("Shane Bolosan", 7.9, [5,5,3,4,5,4,5,4,6], [5,6,5,4,5,4,4,6,6]),
    ("Jeff Cloepfil", 12.0, [5,4,4,6,6,3,3,6,5], [4,7,5,3,5,5,5,5,6]),
    ("Andy Meach", 7.1, [6,4,5,6,6,6,3,5,6], [5,4,4,3,5,4,5,4,7]),
    ("Jon Vrolyks", 5.7, [5,5,4,6,6,6,4,5,7], [4,5,5,4,5,4,4,4,5]),
    ("Mark Lewis", 10.4, [5,4,3,7,6,4,3,4,5], [5,7,5,5,5,5,6,4,5]),
    ("Scott Benton", 12.4, [6,6,4,5,6,4,4,6,7], [5,6,4,3,4,4,4,4,6]),
    ("Jim Restivo", 12.7, [4,5,4,4,3,5,3,7,5], [5,5,5,4,4,8,6,5,7]),
    ("Mike Muller", 7.0, [5,5,4,5,5,5,4,5,6], [5,6,5,4,5,5,4,4,7]),
    ("Chris Beck", 13.2, [4,6,3,7,6,5,2,5,7], [6,5,4,4,6,5,4,4,7]),
    ("Rob Oliver", 17.8, [5,4,4,6,5,5,3,6,7], [6,5,5,3,4,6,4,5,7]),
    ("Win Doolittle", 8.0, [8,4,5,5,5,4,3,6,6], [4,4,6,4,5,4,5,4,8]),
    ("Ron Amstutz", 12.2, [5,5,4,6,5,5,3,5,6], [8,5,6,4,5,5,5,3,6]),
    ("Bud Scott", 9.4, [5,5,4,7,4,5,5,5,5], [4,6,6,3,5,5,6,5,7]),
    ("Matt Neimeier", 12.2, [4,5,4,6,6,5,3,5,7], [4,7,8,3,8,5,4,3,5]),
    ("Dana Beckley", 6.9, [6,5,3,7,6,4,3,6,6], [6,6,7,7,4,4,5,5,6]),
    ("Glenn Brand", 11.1, [5,6,4,7,6,3,4,6,6], [5,6,5,5,5,5,6,5,7]),
    ("Korey Jerome", 9.3, [6,5,3,6,6,5,4,6,6], [5,5,6,3,5,6,6,5,9]),
    ("Mark Albedyll", 14.7, [6,5,5,7,5,6,4,6,4], [5,7,6,5,4,6,7,5,7]),
    ("Patrick Schueppert", 16.8, [8,6,5,5,4,4,5,8,5], [5,7,9,3,5,4,6,5,8])
]

# --- 2. EARNINGS ---
quota_results = [
    ("Derek Becko", 180, 1, 13), ("Rick Meewes", 180, 1, 13),
    ("Christopher Royce", 180, 1, 19), ("Rich Mckeon", 180, 1, 19),
    ("David Pearson", 40, 3, 12), ("Ron Marino", 40, 3, 12)
]

net_medal_results = [
    ("Ben Magnone", 162, 1), ("Kevin Barber", 162, 1),
    ("Christopher Royce", 12, 3), ("Jeff De Laveaga", 12, 3), ("Rick Meewes", 12, 3)
]

gross_skins_results = [
    ("Rick Meewes", 116), ("Travis Ingram", 116), ("Jeff De Laveaga", 58)
]

net_skins_results = [
    ("Chris Beck", 51.43), ("Christopher Royce", 51.43), ("Clark Koch", 51.43),
    ("Dan Denham", 51.43), ("Kevin Barber", 51.43), ("Mark Albedyll", 51.43),
    ("Travis Ingram", 51.43)
]

# --- 3. DATAFRAME CONSTRUCTION ---
def build_dataframes():
    # Raw Scores & Handicaps
    score_data = []
    hcp_data = []
    
    for p, hcp, front, back in raw_data:
        full_score = front + back
        gross = sum(full_score)
        
        row = {'Player': p, 'date': TOURNAMENT_DATE, 'Gross_Score': gross}
        for i, s in enumerate(full_score):
            row[f'H{i+1}'] = s
        score_data.append(row)
        hcp_data.append({'Player': p, 'Handicap': hcp, 'date': TOURNAMENT_DATE})

    df_scores = pd.DataFrame(score_data)
    df_hcp = pd.DataFrame(hcp_data)
    
    # Quota
    df_quota = pd.DataFrame(quota_results, columns=['Player', 'Team_earnings', 'Placement', 'Team_ID'])
    df_quota['date'] = TOURNAMENT_DATE
    
    # Net Medal
    df_net_medal = pd.DataFrame(net_medal_results, columns=['Player', 'net_medal_earnings', 'Placement'])
    df_net_medal['date'] = TOURNAMENT_DATE
    
    # Skins
    df_gskins = pd.DataFrame(gross_skins_results, columns=['Player', 'Gskins_earnings'])
    df_gskins['date'] = TOURNAMENT_DATE
    
    df_nskins = pd.DataFrame(net_skins_results, columns=['Player', 'Nskins_earnings'])
    df_nskins['date'] = TOURNAMENT_DATE
    
    return df_scores, df_hcp, df_quota, df_net_medal, df_gskins, df_nskins

# --- 4. EXPORT ---
def export_excel():
    df_scores, df_hcp, df_quota, df_net_medal, df_gskins, df_nskins = build_dataframes()
    
    output_path = os.path.join("data", "2025-12-20_SG-SG_Data.xlsx")
    
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        df_scores.to_excel(writer, sheet_name='RawScores', index=False)
        df_hcp.to_excel(writer, sheet_name='Handicaps', index=False)
        df_quota.to_excel(writer, sheet_name='Quota', index=False)
        df_net_medal.to_excel(writer, sheet_name='NetMedal', index=False)
        df_gskins.to_excel(writer, sheet_name='GrossSkins', index=False)
        df_nskins.to_excel(writer, sheet_name='NetSkins', index=False)
        
    print(f"✅ Generated {output_path}")

if __name__ == "__main__":
    export_excel()
