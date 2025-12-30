import pandas as pd
import os

# --- Helper: clean placement ---
def clean_place(p):
    return str(p).replace('T', '').strip()

# --- 1. Raw Scores (Gross) ---
raw_data = [
    ["Jeff De Laveaga", 4, 3, 3, 5, 3, 5, 4, 4, 5, 3, 5, 3, 4, 4, 4, 3, 4, 4],
    ["Neil Harris", 4, 4, 3, 4, 4, 4, 4, 5, 6, 4, 5, 3, 3, 4, 4, 3, 4, 5],
    ["Eric Weiss", 4, 4, 3, 4, 5, 4, 3, 4, 5, 4, 5, 4, 4, 4, 5, 5, 4, 5],
    ["Todd Densley", 4, 4, 2, 6, 4, 4, 3, 3, 5, 4, 5, 5, 3, 5, 4, 4, 4, 7],
    ["Rick Meewes", 4, 5, 3, 4, 6, 5, 3, 5, 6, 4, 5, 4, 2, 3, 4, 4, 4, 6],
    ["Ben Magnone", 4, 4, 3, 5, 3, 5, 4, 5, 6, 4, 6, 4, 4, 4, 4, 3, 5, 5],
    ["Derek Becko", 6, 3, 3, 5, 4, 5, 4, 4, 5, 4, 5, 4, 3, 4, 4, 4, 5, 7],
    ["Joe Sepessy", 5, 4, 3, 5, 4, 4, 3, 4, 6, 4, 6, 5, 4, 4, 5, 4, 4, 5],
    ["Justin Deuker", 5, 5, 3, 5, 4, 3, 3, 5, 6, 4, 6, 4, 3, 4, 4, 4, 4, 7],
    ["Kiernan Mattson", 5, 4, 4, 6, 6, 4, 3, 4, 6, 3, 4, 5, 3, 4, 5, 4, 4, 5],
    ["Ron Marino", 4, 5, 4, 5, 4, 3, 3, 4, 4, 5, 5, 5, 3, 5, 4, 5, 4, 7],
    ["Travis Ingram", 3, 5, 4, 6, 4, 5, 3, 4, 5, 4, 6, 6, 3, 5, 4, 3, 2, 7],
    ["Clark Koch", 5, 5, 3, 5, 6, 4, 3, 4, 5, 5, 5, 5, 4, 4, 5, 4, 4, 4],
    ["Paul Benga", 4, 4, 3, 5, 4, 5, 3, 4, 5, 5, 6, 5, 6, 4, 4, 4, 4, 5],
    ["Dan Denham", 5, 6, 4, 5, 4, 4, 3, 3, 6, 4, 5, 5, 3, 5, 5, 4, 4, 6],
    ["Dusty Wasmund", 7, 4, 2, 5, 5, 4, 4, 6, 4, 5, 5, 5, 3, 5, 4, 4, 5, 5],
    ["David Pearson", 6, 4, 3, 6, 5, 5, 3, 4, 5, 5, 6, 5, 3, 5, 5, 4, 3, 6],
    ["Kevin Barber", 6, 4, 2, 5, 5, 4, 4, 5, 5, 5, 6, 6, 3, 4, 5, 5, 3, 7],
    ["Steve McCormick", 5, 5, 3, 5, 5, 4, 3, 5, 5, 5, 5, 5, 4, 4, 5, 5, 4, 7],
    ["Steve Rosenbluth", 4, 4, 4, 6, 5, 4, 3, 6, 6, 4, 6, 5, 4, 5, 4, 4, 4, 6],
    ["Christopher Royce", 4, 5, 3, 4, 4, 5, 3, 4, 6, 5, 4, 7, 5, 7, 4, 5, 4, 6],
    ["Rich McKeon", 4, 4, 3, 6, 4, 5, 4, 4, 5, 5, 6, 4, 6, 5, 5, 5, 4, 7],
    ["Shane Bolosan", 5, 5, 3, 4, 5, 4, 5, 4, 6, 5, 6, 5, 4, 5, 4, 4, 6, 6],
    ["Jeff Cloepfil", 5, 4, 4, 6, 6, 3, 3, 6, 5, 4, 7, 5, 3, 5, 5, 5, 5, 6],
    ["Andy Meach", 6, 4, 5, 6, 6, 6, 3, 5, 6, 5, 4, 4, 3, 5, 4, 5, 4, 7],
    ["Jon Vrolyks", 5, 5, 4, 6, 6, 6, 4, 5, 7, 4, 5, 5, 4, 5, 4, 4, 4, 5],
    ["Mark Lewis", 5, 4, 3, 7, 6, 4, 3, 4, 5, 5, 7, 5, 5, 5, 5, 6, 4, 5],
    ["Scott Benton", 6, 6, 4, 5, 6, 4, 4, 6, 7, 5, 6, 4, 3, 4, 4, 4, 4, 6],
    ["Jim Restivo", 4, 5, 4, 4, 3, 5, 3, 7, 5, 5, 5, 5, 4, 4, 8, 6, 5, 7],
    ["Mike Muller", 5, 5, 4, 5, 5, 5, 4, 5, 6, 5, 6, 5, 4, 5, 5, 4, 4, 7],
    ["Chris Beck", 4, 6, 3, 7, 6, 5, 2, 5, 7, 6, 5, 4, 4, 6, 5, 4, 4, 7],
    ["Rob Oliver", 5, 4, 4, 6, 5, 5, 3, 6, 7, 6, 5, 5, 3, 4, 6, 4, 5, 7],
    ["Win Doolittle", 8, 4, 5, 5, 5, 4, 3, 6, 6, 4, 4, 6, 4, 5, 4, 5, 4, 8],
    ["Ron Amstutz", 5, 5, 4, 6, 5, 5, 3, 5, 6, 8, 5, 6, 4, 5, 5, 5, 3, 6],
    ["Bud Scott", 5, 5, 4, 7, 4, 5, 5, 5, 5, 4, 6, 6, 3, 5, 5, 6, 5, 7],
    ["Matt Neimeier", 4, 5, 4, 6, 6, 5, 3, 5, 7, 4, 7, 8, 3, 8, 5, 4, 3, 5],
    ["Dana Beckley", 6, 5, 3, 7, 6, 4, 3, 6, 6, 6, 6, 7, 7, 4, 4, 5, 5, 6],
    ["Glenn Brand", 5, 6, 4, 7, 6, 3, 4, 6, 6, 5, 6, 5, 5, 5, 5, 6, 5, 7],
    ["Korey Jerome", 6, 5, 3, 6, 6, 5, 4, 6, 6, 5, 5, 6, 3, 5, 6, 6, 5, 9],
    ["Mark Albedyll", 6, 5, 5, 7, 5, 6, 4, 6, 4, 5, 7, 6, 5, 4, 6, 7, 5, 7],
    ["Patrick Schueppert", 8, 6, 5, 5, 4, 4, 5, 8, 5, 5, 7, 9, 3, 5, 4, 6, 5, 8]
]
cols = ['Player'] + [f'H{i}' for i in range(1, 19)]
df_raw = pd.DataFrame(raw_data, columns=cols)
df_raw['date'] = '2025-12-20'

# --- 2. Net Medal ---
net_medal_data = [
    ["Ben Magnone", "1", 162],
    ["Kevin Barber", "1", 162],
    ["Christopher Royce", "3", 12],
    ["Jeff De Laveaga", "3", 12],
    ["Rick Meewes", "3", 12]
]
df_net = pd.DataFrame(net_medal_data, columns=["Player", "Placement", "net_medal_earnings"])
df_net['date'] = '2025-12-20'

# --- 3. Gross Skins ---
gross_skins_data = [
    ["Rick Meewes", 116],
    ["Travis Ingram", 116],
    ["Jeff De Laveaga", 58]
]
df_gross_skins = pd.DataFrame(gross_skins_data, columns=["Player", "Gskins_earnings"])
df_gross_skins['date'] = '2025-12-20'

# --- 4. Net Skins ---
net_skins_data = [
    ["Chris Beck", 51.43],
    ["Christopher Royce", 51.43],
    ["Clark Koch", 51.43],
    ["Dan Denham", 51.43],
    ["Kevin Barber", 51.43],
    ["Mark Albedyll", 51.43],
    ["Travis Ingram", 51.43]
]
df_net_skins = pd.DataFrame(net_skins_data, columns=["Player", "Nskins_earnings"])
df_net_skins['date'] = '2025-12-20'

# --- 5. Quota (Teams) ---
quota_data = [
    ["Derek Becko", "Team 13", "1", 180],
    ["Rick Meewes", "Team 13", "1", 180],
    ["Christopher Royce", "Team 19", "1", 180],
    ["Rich McKeon", "Team 19", "1", 180],
    ["David Pearson", "Team 12", "3", 40],
    ["Ron Marino", "Team 12", "3", 40],
    ["Clark Koch", "Team 14", "4", 0],
    ["Eric Weiss", "Team 14", "4", 0],
    ["Travis Ingram", "Team 2", "5", 0],
    ["Win Doolittle", "Team 2", "5", 0],
    ["Jim Restivo", "Team 5", "5", 0],
    ["Steve Rosenbluth", "Team 5", "5", 0],
    ["Dusty Wasmund", "Team 6", "5", 0],
    ["Kiernan Mattson", "Team 6", "5", 0],
    ["Glenn Brand", "Team 8", "5", 0],
    ["Jeff De Laveaga", "Team 8", "5", 0],
    ["Chris Beck", "Team 15", "9", 0],
    ["Rob Oliver", "Team 15", "9", 0],
    ["Dan Denham", "Team 16", "10", 0],
    ["Matt Neimeier", "Team 16", "10", 0],
    ["Jeff Cloepfil", "Team 4", "11", 0],
    ["Scott Benton", "Team 4", "11", 0],
    ["Mark Lewis", "Team 18", "12", 0],
    ["Todd Densley", "Team 18", "12", 0],
    ["Patrick Schueppert", "Team 1", "13", 0],
    ["Ron Amstutz", "Team 1", "13", 0],
    ["Kevin Barber", "Team 9", "13", 0],
    ["Korey Jerome", "Team 9", "13", 0],
    ["Mike Muller", "Team 10", "13", 0],
    ["Neil Harris", "Team 10", "13", 0],
    ["Andy Meach", "Team 7", "16", 0],
    ["Paul Benga", "Team 7", "16", 0],
    ["Joe Sepessy", "Team 11", "16", 0],
    ["Jon Vrolyks", "Team 11", "16", 0],
    ["Bud Scott", "Team 17", "18", 0],
    ["Justin Deuker", "Team 17", "18", 0],
    ["Mark Albedyll", "Team 3", "19", 0],
    ["Shane Bolosan", "Team 3", "19", 0],
    ["Dana Beckley", "Team 20", "20", 0],
    ["Steve McCormick", "Team 20", "20", 0]
]
df_quota = pd.DataFrame(quota_data, columns=["Player", "Team_ID", "Placement", "Team_earnings"])
df_quota['date'] = '2025-12-20'

# --- 6. Handicaps ---
handicap_data = [
    ["Andy Meach", 7.1],
    ["Ben Magnone", 10.4],
    ["Bud Scott", 9.4],
    ["Chris Beck", 13.2],
    ["Christopher Royce", 13.9],
    ["Clark Koch", 8.8],
    ["Dan Denham", 6.5],
    ["Dana Beckley", 6.9],
    ["David Pearson", 9.6],
    ["Derek Becko", 3.5],
    ["Dusty Wasmund", 7.6],
    ["Eric Weiss", 1.0],
    ["Glenn Brand", 11.1],
    ["Jeff Cloepfil", 12.0],
    ["Jeff De Laveaga", 0.5],
    ["Jim Restivo", 12.7],
    ["Joe Sepessy", 6.1],
    ["Jon Vrolyks", 5.7],
    ["Justin Deuker", 3.0],
    ["Kevin Barber", 15.3],
    ["Kiernan Mattson", 1.4],
    ["Korey Jerome", 9.3],
    ["Mark Albedyll", 14.7],
    ["Mark Lewis", 10.4],
    ["Matt Neimeier", 12.2],
    ["Mike Muller", 7.0],
    ["Neil Harris", -1.7], # Was +1.7, now negative for formula
    ["Patrick Schueppert", 16.8],
    ["Paul Benga", 4.2],
    ["Rich McKeon", 11.0],
    ["Rick Meewes", 6.5],
    ["Rob Oliver", 17.8],
    ["Ron Amstutz", 12.2],
    ["Ron Marino", 7.2],
    ["Scott Benton", 12.4],
    ["Shane Bolosan", 7.9],
    ["Steve McCormick", 9.2],
    ["Steve Rosenbluth", 8.4],
    ["Todd Densley", -0.8], # Was +0.8, now negative for formula
    ["Travis Ingram", 6.6],
    ["Win Doolittle", 8.0]
]
df_handicaps = pd.DataFrame(handicap_data, columns=["Player", "HI"])
df_handicaps['date'] = '2025-12-20'

# --- 7. Save to Excel ---
with pd.ExcelWriter('2025-12-20_SG-SG_Data.xlsx') as writer:
    df_raw.to_excel(writer, sheet_name='RawScores', index=False)
    df_net.to_excel(writer, sheet_name='NetMedal', index=False)
    df_gross_skins.to_excel(writer, sheet_name='GrossSkins', index=False)
    df_net_skins.to_excel(writer, sheet_name='NetSkins', index=False)
    df_quota.to_excel(writer, sheet_name='Quota', index=False)
    df_handicaps.to_excel(writer, sheet_name='Handicaps', index=False)

print("✅ Excel file created successfully with Handicaps and Clean Placements!")