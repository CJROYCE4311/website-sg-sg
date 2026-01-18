import pandas as pd
import glob
import os
import sys
from datetime import datetime

# Setup paths
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
DB_DIR = os.path.join(DATA_DIR, "db")

def clean_df(df, default_date=None):
    if df.empty: return df
    df.columns = [str(c).strip() for c in df.columns]
    
    # Standardize Date
    d_col = next((c for c in df.columns if c.lower() == 'date'), None)
    if d_col:
        df[d_col] = pd.to_datetime(df[d_col], errors='coerce')
        df = df.rename(columns={d_col: 'Date'})
    elif default_date:
        df['Date'] = default_date

    # Standardize Player column
    p_col = next((c for c in df.columns if c.lower() in ['player', 'name']), None)
    if p_col:
        df = df.rename(columns={p_col: 'Player'})
        df['Player'] = df['Player'].astype(str).str.strip().str.title()
    
    return df

def to_numeric_safe(df, cols):
    for col in cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace('$', '').str.replace(',', '').str.strip(), errors='coerce').fillna(0.0)
    return df

def migrate():
    print("🚀 Starting Migration to CSV Database...")
    
    excel_files = sorted(glob.glob(os.path.join(DATA_DIR, "2*.xlsx")))
    if not excel_files:
        print("❌ No Excel files found to migrate.")
        return

    all_scores = []
    all_financials = []
    all_handicaps = []

    for f in excel_files:
        filename = os.path.basename(f)
        print(f"  Reading {filename}...")
        
        # Extract date from filename as fallback
        try:
            date_part = filename[:10]
            file_date = pd.to_datetime(date_part)
        except:
            file_date = None

        xls = pd.read_excel(f, sheet_name=None)
        
        # Pre-clean sheets with file_date fallback
        cleaned_sheets = {k: clean_df(v, default_date=file_date) for k, v in xls.items()}
        
        # 1. SCORES & ROUND-LEVEL HANDICAPS
        if 'RawScores' in cleaned_sheets:
            df = cleaned_sheets['RawScores']
            # Ensure H1-H18 and Gross_Score
            score_cols = [f'H{i}' for i in range(1, 19)] + ['Gross_Score']
            df = to_numeric_safe(df, score_cols)
            
            # Get Handicap used for the round
            if 'Handicaps' in cleaned_sheets:
                h_val = cleaned_sheets['Handicaps']
                if 'Player' in df.columns and 'Player' in h_val.columns:
                    h_col = next((c for c in h_val.columns if c in ['Handicap', 'HI', 'Handicap_Index']), None)
                    if h_col:
                        h_val_subset = h_val.rename(columns={h_col: 'Round_Handicap'})
                        h_val_subset = to_numeric_safe(h_val_subset, ['Round_Handicap'])
                        
                        merge_cols = ['Player']
                        if 'Date' in h_val_subset.columns and 'Date' in df.columns:
                            merge_cols.append('Date')
                        
                        df = df.merge(h_val_subset[merge_cols + ['Round_Handicap']], on=merge_cols, how='left')

            # Only keep rows that have a Date and Player
            if 'Date' in df.columns and 'Player' in df.columns:
                cols_to_keep = ['Date', 'Player'] + [c for c in score_cols if c in df.columns]
                if 'Round_Handicap' in df.columns:
                    cols_to_keep.append('Round_Handicap')
                all_scores.append(df[cols_to_keep])

        # 2. FINANCIALS (Consolidate all earning types)
        finance_sheets = {
            'NetMedal': 'NetMedal',
            'BB': 'BestBall',
            'Team': 'BestBall',
            'Quota': 'Quota',
            'GrossSkins': 'GrossSkins',
            'NetSkins': 'NetSkins'
        }
        
        for sheet, cat in finance_sheets.items():
            if sheet in cleaned_sheets:
                df = cleaned_sheets[sheet]
                # Find earnings column
                e_col = next((c for c in df.columns if 'earn' in c.lower()), None)
                if e_col:
                    df = to_numeric_safe(df, [e_col])
                    if 'Date' in df.columns and 'Player' in df.columns:
                        temp_df = df[['Date', 'Player', e_col]].copy()
                        temp_df = temp_df.rename(columns={e_col: 'Amount'})
                        temp_df['Category'] = cat
                        all_financials.append(temp_df)

        # 3. HANDICAPS (Time Series)
        if 'Handicaps' in cleaned_sheets:
            df = cleaned_sheets['Handicaps']
            h_col = next((c for c in df.columns if c.lower() in ['handicap', 'hi', 'handicap_index']), None)
            if h_col:
                df = df.rename(columns={h_col: 'Handicap_Index'})
                df = to_numeric_safe(df, ['Handicap_Index'])
                if 'Date' in df.columns and 'Player' in df.columns:
                    all_handicaps.append(df[['Date', 'Player', 'Handicap_Index']])

    # Consolidate and Save
    if all_scores:
        scores_df = pd.concat(all_scores, ignore_index=True).drop_duplicates()
        scores_df.to_csv(os.path.join(DB_DIR, "scores.csv"), index=False)
        print(f"✅ Saved {len(scores_df)} scores to scores.csv")

    if all_financials:
        fin_df = pd.concat(all_financials, ignore_index=True)
        # Sum duplicates if any (same person, same cat, same day)
        fin_df = fin_df.groupby(['Date', 'Player', 'Category'])['Amount'].sum().reset_index()
        fin_df = fin_df[fin_df['Amount'] > 0]
        fin_df.to_csv(os.path.join(DB_DIR, "financials.csv"), index=False)
        print(f"✅ Saved {len(fin_df)} financial records to financials.csv")

    if all_handicaps:
        h_df = pd.concat(all_handicaps, ignore_index=True).drop_duplicates()
        h_df.to_csv(os.path.join(DB_DIR, "handicaps.csv"), index=False)
        print(f"✅ Saved {len(h_df)} handicap snapshots to handicaps.csv")

    print("\n🎉 Migration Complete! Your database is now CSV-based.")

if __name__ == "__main__":
    migrate()
