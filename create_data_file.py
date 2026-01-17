import pandas as pd
import os

# Data Setup
date_str = '2026-01-17'
output_file = f'data/{date_str}_SG-SG_Data.xlsx'

# 1. Raw Scores
raw_data = [
    # Player, H1..H18
    ['Jared Strathe', 4,3,3,4,4,3,3,4,5, 4,4,5,4,3,4,3,2,5],
    ['James Feutz', 4,3,3,5,4,4,4,4,5, 5,4,4,3,4,3,3,3,4],
    ['Nate Adams', 4,3,3,5,5,4,3,3,4, 4,4,4,3,5,4,4,3,5],
    ['Eric Weiss', 4,4,3,5,4,5,3,4,4, 4,4,4,3,4,5,5,3,3],
    ['Jeff De Laveaga', 4,4,3,4,4,5,4,4,5, 4,5,4,3,4,4,3,3,5],
    ['Matt Pullen', 5,4,3,5,5,3,2,4,4, 4,5,3,5,4,4,3,4,6],
    ['Kiernan Mattson', 5,5,3,5,4,4,3,5,5, 4,5,4,3,4,4,3,4,4],
    ['Rick Meewes', 4,4,3,5,5,5,5,3,5, 5,5,4,3,3,4,3,3,5],
    ['Paul Benga', 5,4,4,6,4,5,3,4,5, 3,6,4,2,4,4,5,3,6],
    ['Scott Bracken', 4,4,2,6,6,3,4,5,4, 5,5,5,4,3,4,4,4,5],
    ['Scott Lucas', 4,4,3,5,4,5,4,5,5, 3,4,6,4,5,4,3,3,6],
    ['Greg Funk', 4,4,3,5,4,4,3,5,6, 4,5,4,4,5,5,4,4,5],
    ['Todd Densley', 3,4,3,5,4,4,6,5,5, 5,5,4,4,4,4,3,4,6],
    ['Justin Deuker', 6,5,3,6,4,5,4,5,5, 4,5,4,3,3,4,5,4,5],
    ['Rich Fagan', 3,4,4,7,5,7,4,3,5, 4,5,4,5,3,4,5,3,5],
    ['Andy Meach', 5,4,2,6,4,5,4,4,5, 4,6,5,6,4,4,4,4,5],
    ['Chris Husong', 4,5,4,5,4,4,4,4,7, 5,5,4,4,4,5,4,4,5],
    ['Frank Angeloro', 4,5,3,8,6,4,4,4,5, 4,5,4,4,5,5,3,3,5],
    ['Dusty Wasmund', 5,5,4,5,5,6,2,5,6, 4,5,4,6,4,4,4,3,5],
    ['Jon Vrolyks', 6,4,3,5,5,4,4,4,5, 5,6,4,5,4,4,4,4,6],
    ['Korey Jerome', 5,3,3,4,4,6,4,5,6, 4,8,4,4,4,6,3,3,6],
    ['David Adams', 7,5,4,5,5,3,3,5,5, 4,6,5,4,6,4,3,3,6],
    ['Steve Rosenbluth', 5,4,3,6,5,5,5,5,6, 4,5,4,5,4,4,4,4,5],
    ['Thomas Earl', 5,4,3,6,5,6,5,5,5, 4,4,4,3,5,5,5,3,6],
    ['Travis Ingram', 5,5,4,5,5,4,4,4,5, 5,6,6,4,4,4,5,3,6],
    ['Jamey Davis', 4,4,3,5,5,4,5,6,6, 3,6,5,5,5,3,6,4,6],
    ['Shawn Warner', 4,4,4,6,6,4,5,5,5, 4,5,5,5,3,6,4,4,6],
    ['Glenn Brand', 6,5,3,7,5,4,4,4,5, 4,6,6,3,6,4,5,4,6],
    ['Richard Lederman', 4,5,3,6,5,4,3,4,7, 7,6,5,3,4,4,5,5,7],
    ['Ron Amstutz', 6,4,4,6,5,3,3,6,5, 4,6,4,5,4,4,5,3,10],
    ['Jim Restivo', 6,6,3,5,5,6,5,6,7, 5,5,5,3,4,4,4,4,5],
    ['Mark Lewis', 5,5,3,5,6,4,4,5,6, 5,6,4,4,6,4,5,3,8],
    ['Rick Deloney', 5,6,3,6,5,4,4,5,6, 5,7,5,4,4,4,5,4,6],
    ['Patrick Schueppert', 4,6,3,6,5,4,3,4,6, 5,6,6,4,5,6,5,3,8],
    ['Chris Ryan', 3,4,3,6,5,6,6,4,6, 6,6,6,4,7,5,3,4,6],
    ['Buddy Goldstone', 5,5,4,5,6,6,4,7,5, 5,6,5,6,4,4,4,4,7],
    ['Christopher Royce', 6,4,5,8,5,4,4,5,4, 5,6,6,6,5,5,3,4,8],
    ['Scott Benton', 7,4,4,7,4,7,6,5,6, 5,6,5,3,7,5,4,3,6],
    ['Ken VonWald', 4,7,2,7,8,5,6,5,6, 6,6,5,5,4,6,3,4,6],
    ['Kevin Barber', 6,5,5,7,7,4,4,6,5, 5,5,5,5,5,6,5,5,6]
]

cols = ['Player'] + [f'H{i}' for i in range(1, 19)]
df_raw = pd.DataFrame(raw_data, columns=cols)
df_raw['date'] = date_str
df_raw['Gross_Score'] = df_raw.iloc[:, 1:19].sum(axis=1)

# 2. Handicaps
# Note: Plus handicaps are negative
handicaps = [
    ('Chris Husong', 8.1),
    ('Scott Lucas', 11.8),
    ('Jamey Davis', 13.0),
    ('Kiernan Mattson', 2.8),
    ('Nate Adams', -5.7),
    ('Rich Fagan', 11.7),
    ('David Adams', 8.4),
    ('Patrick Schueppert', 16.8),
    ('Jeff De Laveaga', 0.0),
    ('Ron Amstutz', 12.4),
    ('Frank Angeloro', 8.6),
    ('Richard Lederman', 13.6),
    ('Christopher Royce', 13.4),
    ('Korey Jerome', 10.6),
    ('Dusty Wasmund', 9.1),
    ('Eric Weiss', 0.5),
    ('Ken VonWald', 14.2),
    ('Paul Benga', 4.8),
    ('Andy Meach', 7.5),
    ('James Feutz', -1.6),
    ('Jared Strathe', -4.6),
    ('Matt Pullen', -0.1),
    ('Scott Bracken', 9.8),
    ('Rick Meewes', 3.8),
    ('Shawn Warner', 12.6),
    ('Greg Funk', 5.5),
    ('Todd Densley', 0.0),
    ('Justin Deuker', 3.7),
    ('Jon Vrolyks', 6.0),
    ('Steve Rosenbluth', 9.4),
    ('Thomas Earl', 4.3),
    ('Travis Ingram', 6.8),
    ('Glenn Brand', 10.9),
    ('Jim Restivo', 12.7),
    ('Mark Lewis', 10.5),
    ('Rick Deloney', 7.3),
    ('Chris Ryan', 14.8),
    ('Buddy Goldstone', 12.8),
    ('Scott Benton', 12.0),
    ('Kevin Barber', 16.4)
]
df_hcp = pd.DataFrame(handicaps, columns=['Player', 'Handicap'])
df_hcp['date'] = date_str

# 3. Best Ball (Teams)
bb_data = [
    ('Chris Husong', 1, 240.00),
    ('Scott Lucas', 1, 240.00),
    ('Jamey Davis', 2, 26.67),
    ('Kiernan Mattson', 2, 26.67),
    ('Nate Adams', 2, 26.67),
    ('Rich Fagan', 2, 26.67),
    ('David Adams', 2, 26.67),
    ('Patrick Schueppert', 2, 26.67),
    ('Jeff De Laveaga', 2, 26.67),
    ('Ron Amstutz', 2, 26.67),
    ('Frank Angeloro', 2, 26.67),
    ('Richard Lederman', 2, 26.67),
    ('Christopher Royce', 2, 26.67),
    ('Korey Jerome', 2, 26.67)
]
df_bb = pd.DataFrame(bb_data, columns=['Player', 'Placement', 'BB_earnings'])

# 4. Skins - Net
net_skins_data = [
    ('Christopher Royce', 42.50),
    ('Dusty Wasmund', 42.50),
    ('Eric Weiss', 42.50),
    ('Jamey Davis', 42.50),
    ('Ken VonWald', 42.50),
    ('Korey Jerome', 42.50),
    ('Paul Benga', 42.50),
    ('Rich Fagan', 42.50)
]
df_ns = pd.DataFrame(net_skins_data, columns=['Player', 'Nskins_earnings'])

# 5. Skins - Gross
gross_skins_data = [
    ('Paul Benga', 68.57),
    ('Andy Meach', 34.29),
    ('Eric Weiss', 34.29),
    ('James Feutz', 34.29),
    ('Jared Strathe', 34.29),
    ('Matt Pullen', 34.29)
]
df_gs = pd.DataFrame(gross_skins_data, columns=['Player', 'Gskins_earnings'])

# 6. Net Medal
net_medal_data = [
    ('Scott Lucas', '1', 166.50),
    ('Rich Fagan', 'T2', 74.00),
    ('Scott Bracken', 'T2', 74.00),
    ('Rick Meewes', '4', 37.00),
    ('Eric Weiss', 'T5', 2.64),
    ('James Feutz', 'T5', 2.64),
    ('Jamey Davis', 'T5', 2.64),
    ('Kiernan Mattson', 'T5', 2.64),
    ('Korey Jerome', 'T5', 2.64),
    ('Patrick Schueppert', 'T5', 2.64),
    ('Shawn Warner', 'T5', 2.64)
]
df_nm = pd.DataFrame(net_medal_data, columns=['Player', 'Placement', 'net_medal_earnings'])

# Save to Excel
with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
    df_raw.to_excel(writer, sheet_name='RawScores', index=False)
    df_hcp.to_excel(writer, sheet_name='Handicaps', index=False)
    df_bb.to_excel(writer, sheet_name='BB', index=False)
    df_ns.to_excel(writer, sheet_name='NetSkins', index=False)
    df_gs.to_excel(writer, sheet_name='GrossSkins', index=False)
    df_nm.to_excel(writer, sheet_name='NetMedal', index=False)

print(f"Created {output_file}")
