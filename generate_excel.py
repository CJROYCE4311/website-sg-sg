import pandas as pd
import os

# --- 1. Raw Scores (Gross) ---
raw_data = [
    # Player, H1, H2, ..., H18
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
# Based on netmedal.png
net_medal_data = [
    ["Ben Magnone", "T1", 162],
    ["Kevin Barber", "T1", 162],
    ["Christopher Royce", "T3", 12],
    ["Jeff De Laveaga", "T3", 12],
    ["Rick Meewes", "T3", 12]
]
df_net = pd.DataFrame(net_medal_data, columns=["Player", "Placement", "net_medal_earnings"])
df_net['date'] = '2025-12-20'

# --- 3. Gross Skins ---
# Based on grossskins.png
# Rick Meewes $116, Travis Ingram $116, Jeff De Laveaga $58
gross_skins_data = [
    ["Rick Meewes", 116],
    ["Travis Ingram", 116],
    ["Jeff De Laveaga", 58]
]
df_gross_skins = pd.DataFrame(gross_skins_data, columns=["Player", "Gskins_earnings"])
df_gross_skins['date'] = '2025-12-20'

# --- 4. Net Skins ---
# Based on netskins.png
# Everyone $51.43: Chris Beck, Christopher Royce, Clark Koch, Dan Denham, Kevin Barber, Mark Albedyll, Travis Ingram
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
# Note: Team Earnings in Quota sheet are usually total per team
quota_data = [
    ["Derek Becko", "Team 13", "T1", 180],
    ["Rick Meewes", "Team 13", "T1", 180],
    ["Christopher Royce", "Team 19", "T1", 180],
    ["Rich McKeon", "Team 19", "T1", 180],
    ["David Pearson", "Team 12", "3", 40],
    ["Ron Marino", "Team 12", "3", 40],
    ["Clark Koch", "Team 14", "4", 0],
    ["Eric Weiss", "Team 14", "4", 0],
    ["Travis Ingram", "Team 2", "T5", 0],
    ["Win Doolittle", "Team 2", "T5", 0],
    ["Jim Restivo", "Team 5", "T5", 0],
    ["Steve Rosenbluth", "Team 5", "T5", 0],
    ["Dusty Wasmund", "Team 6", "T5", 0],
    ["Kiernan Mattson", "Team 6", "T5", 0],
    ["Glenn Brand", "Team 8", "T5", 0],
    ["Jeff De Laveaga", "Team 8", "T5", 0],
    ["Chris Beck", "Team 15", "9", 0],
    ["Rob Oliver", "Team 15", "9", 0],
    ["Dan Denham", "Team 16", "10", 0],
    ["Matt Neimeier", "Team 16", "10", 0],
    ["Jeff Cloepfil", "Team 4", "11", 0],
    ["Scott Benton", "Team 4", "11", 0],
    ["Mark Lewis", "Team 18", "12", 0],
    ["Todd Densley", "Team 18", "12", 0],
    ["Patrick Schueppert", "Team 1", "T13", 0],
    ["Ron Amstutz", "Team 1", "T13", 0],
    ["Kevin Barber", "Team 9", "T13", 0],
    ["Korey Jerome", "Team 9", "T13", 0],
    ["Mike Muller", "Team 10", "T13", 0],
    ["Neil Harris", "Team 10", "T13", 0],
    ["Andy Meach", "Team 7", "T16", 0],
    ["Paul Benga", "Team 7", "T16", 0],
    ["Joe Sepessy", "Team 11", "T16", 0],
    ["Jon Vrolyks", "Team 11", "T16", 0],
    ["Bud Scott", "Team 17", "18", 0],
    ["Justin Deuker", "Team 17", "18", 0],
    ["Mark Albedyll", "Team 3", "19", 0],
    ["Shane Bolosan", "Team 3", "19", 0],
    ["Dana Beckley", "Team 20", "20", 0],
    ["Steve McCormick", "Team 20", "20", 0]
]
df_quota = pd.DataFrame(quota_data, columns=["Player", "Team_ID", "Placement", "Team_earnings"])
df_quota['date'] = '2025-12-20'

# --- 6. Save to Excel ---
# We use 'Quota' tab for the team game this time
with pd.ExcelWriter('2025-12-20_SG-SG_Data.xlsx') as writer:
    df_raw.to_excel(writer, sheet_name='RawScores', index=False)
    df_net.to_excel(writer, sheet_name='NetMedal', index=False)
    df_gross_skins.to_excel(writer, sheet_name='GrossSkins', index=False)
    df_net_skins.to_excel(writer, sheet_name='NetSkins', index=False)
    df_quota.to_excel(writer, sheet_name='Quota', index=False)

print("✅ Excel file created successfully!")
