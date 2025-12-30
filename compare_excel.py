import pandas as pd
import numpy as np

new_file = '2025-12-20_SG-SG_Data.xlsx'
old_file = 'OLD_2025-12-20_SG-SG_Data.xlsx'

try:
    new_xls = pd.read_excel(new_file, sheet_name=None)
    old_xls = pd.read_excel(old_file, sheet_name=None)
except Exception as e:
    print(f"Error reading files: {e}")
    exit()

print(f"--- Comparing {old_file} (OLD) vs {new_file} (NEW) ---\n")

all_sheets = set(new_xls.keys()) | set(old_xls.keys())

for sheet in sorted(all_sheets):
    print(f"🔍 SHEET: {sheet}")
    
    if sheet not in old_xls:
        print(f"   ⚠️  ONLY in NEW file (Rows: {len(new_xls[sheet])})")
        continue
    if sheet not in new_xls:
        print(f"   ⚠️  ONLY in OLD file (Rows: {len(old_xls[sheet])})")
        continue

    df_new = new_xls[sheet]
    df_old = old_xls[sheet]

    # Normalize column names
    df_new.columns = [str(c).strip() for c in df_new.columns]
    df_old.columns = [str(c).strip() for c in df_old.columns]

    # Compare Dimensions
    if df_new.shape != df_old.shape:
        print(f"   ❌ Shape Mismatch: OLD {df_old.shape} vs NEW {df_new.shape}")
    else:
        print(f"   ✅ Dimensions Match: {df_new.shape}")

    # Compare Columns
    new_cols = set(df_new.columns)
    old_cols = set(df_old.columns)
    if new_cols != old_cols:
        added = new_cols - old_cols
        removed = old_cols - new_cols
        if added: print(f"   ➕ Added Columns: {added}")
        if removed: print(f"   ➖ Removed Columns: {removed}")
    
    # Compare Data (Approximate)
    try:
        # Attempt to find a common key (usually 'Player' or 'Name')
        key_col = next((c for c in df_new.columns if c.lower() in ['player', 'name']), None)
        
        if key_col and key_col in df_old.columns:
            merged = df_old.merge(df_new, on=key_col, how='outer', suffixes=('_old', '_new'), indicator=True)
            
            # Rows only in one
            in_old = merged[merged['_merge'] == 'left_only']
            in_new = merged[merged['_merge'] == 'right_only']
            
            if not in_old.empty:
                print(f"   ➖ {len(in_old)} Rows removed (Examples: {in_old[key_col].head(3).tolist()})")
            
            if not in_new.empty:
                print(f"   ➕ {len(in_new)} Rows added (Examples: {in_new[key_col].head(3).tolist()})")
                
        else:
            print("   ℹ️  No common 'Player' column found for row-by-row comparison.")

    except Exception as e:
        print(f"   ⚠️  Could not perform deep row comparison: {e}")

    print("-" * 30)