import pandas as pd
import os
import json
import argparse
import sys
import subprocess
from datetime import datetime

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
DB_DIR = os.path.join(PROJECT_ROOT, "data")

SCORES_FILE = os.path.join(DB_DIR, "scores.csv")
FINANCIALS_FILE = os.path.join(DB_DIR, "financials.csv")
HANDICAPS_FILE = os.path.join(DB_DIR, "handicaps.csv")

def load_db():
    scores = pd.read_csv(SCORES_FILE) if os.path.exists(SCORES_FILE) else pd.DataFrame()
    financials = pd.read_csv(FINANCIALS_FILE) if os.path.exists(FINANCIALS_FILE) else pd.DataFrame()
    handicaps = pd.read_csv(HANDICAPS_FILE) if os.path.exists(HANDICAPS_FILE) else pd.DataFrame()
    return scores, financials, handicaps

def save_db(scores, financials, handicaps):
    scores.to_csv(SCORES_FILE, index=False)
    financials.to_csv(FINANCIALS_FILE, index=False)
    handicaps.to_csv(HANDICAPS_FILE, index=False)
    print("✅ Database saved successfully.")

def process_entry(data, current_scores, current_financials, current_handicaps):
    date_str = data.get('date')
    if not date_str:
        print("❌ Error: Entry missing 'date' field.")
        return current_scores, current_financials, current_handicaps
        
    print(f"📅 Processing Date: {date_str}")
    
    # 1. Process Scores
    new_scores = data.get('scores', [])
    if new_scores:
        df_new = pd.DataFrame(new_scores)
        df_new['Date'] = date_str
        
        if not current_scores.empty:
            # Ensure index columns exist
            if 'Date' in current_scores.columns and 'Player' in current_scores.columns:
                # Upsert Logic: Update existing rows, append new ones
                # Convert Date column to string to ensure matching
                current_scores['Date'] = current_scores['Date'].astype(str)
                
                current_scores = current_scores.set_index(['Date', 'Player'])
                df_new = df_new.set_index(['Date', 'Player'])
                
                # Update existing entries
                current_scores.update(df_new)
                
                # Find new entries
                new_indices = df_new.index.difference(current_scores.index)
                df_new_entries = df_new.loc[new_indices]
                
                # Combine
                current_scores = pd.concat([current_scores, df_new_entries])
                current_scores.reset_index(inplace=True)
                
                print(f"   ✅ Scores: Updated existing, added {len(df_new_entries)} new.")
            else:
                current_scores = pd.concat([current_scores, df_new], ignore_index=True)
                print(f"   ✅ Added {len(df_new)} new scores (fallback).")
        else:
            current_scores = df_new
            print(f"   ✅ Added {len(df_new)} new scores.")

    # 2. Process Financials
    new_fin = data.get('financials', [])
    if new_fin:
        df_fin = pd.DataFrame(new_fin)
        df_fin['Date'] = date_str
        current_financials = pd.concat([current_financials, df_fin], ignore_index=True)
        print(f"   ✅ Added {len(df_fin)} financial records.")

    # 3. Process Handicaps
    new_hcp = data.get('handicaps', [])
    if new_hcp:
        df_hcp = pd.DataFrame(new_hcp)
        df_hcp['Date'] = date_str
        
        if not current_handicaps.empty:
            current_handicaps['Date'] = current_handicaps['Date'].astype(str)
            existing_keys = set(zip(current_handicaps['Date'], current_handicaps['Player']))
            duplicates = set(zip(df_hcp['Date'], df_hcp['Player'])).intersection(existing_keys)
             
            if duplicates:
                 df_hcp = df_hcp[~df_hcp.apply(lambda x: (x['Date'], x['Player']) in duplicates, axis=1)]
        
        if not df_hcp.empty:
            current_handicaps = pd.concat([current_handicaps, df_hcp], ignore_index=True)
            print(f"   ✅ Added {len(df_hcp)} handicap records.")
            
    return current_scores, current_financials, current_handicaps

def ingest(json_file):
    print(f"📥 Ingesting {json_file}...")
    
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    current_scores, current_financials, current_handicaps = load_db()
    
    if 'update_batch' in data:
        print(f"📦 Batch Update Detected: {len(data['update_batch'])} entries.")
        for entry in data['update_batch']:
            current_scores, current_financials, current_handicaps = process_entry(
                entry, current_scores, current_financials, current_handicaps
            )
    else:
        current_scores, current_financials, current_handicaps = process_entry(
            data, current_scores, current_financials, current_handicaps
        )

    save_db(current_scores, current_financials, current_handicaps)
    
    # Trigger Site Update
    print("\n🔄 Triggering Site Update...")
    venv_python = os.path.join(PROJECT_ROOT, "venv", "bin", "python")
    if not os.path.exists(venv_python):
        venv_python = "python" # Fallback
        
    subprocess.run([venv_python, os.path.join(SCRIPT_DIR, "update_site.py")])

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest new tournament data.")
    parser.add_argument("input_file", help="Path to JSON file containing new data.")
    args = parser.parse_args()
    
    if not os.path.exists(args.input_file):
        print(f"❌ Input file not found: {args.input_file}")
        sys.exit(1)
        
    ingest(args.input_file)
