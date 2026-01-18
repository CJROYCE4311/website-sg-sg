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

def ingest(json_file):
    print(f"📥 Ingesting {json_file}...")
    
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    # Expected JSON structure:
    # {
    #   "date": "YYYY-MM-DD",
    #   "scores": [ {"Player": "Name", "H1": 4, ... "H18": 5, "Gross_Score": 72, "Round_Handicap": 5} ],
    #   "financials": [ {"Player": "Name", "Category": "NetSkins", "Amount": 50} ],
    #   "handicaps": [ {"Player": "Name", "Handicap_Index": 5.4} ]
    # }

    date_str = data.get('date')
    if not date_str:
        print("❌ Error: JSON must contain a 'date' field (YYYY-MM-DD).")
        sys.exit(1)
        
    print(f"📅 Date: {date_str}")
    
    current_scores, current_financials, current_handicaps = load_db()
    
    # 1. Process Scores
    new_scores = data.get('scores', [])
    if new_scores:
        df_new = pd.DataFrame(new_scores)
        df_new['Date'] = date_str
        
        # Check for duplicates
        if not current_scores.empty:
            # Create a composite key for checking
            existing_keys = set(zip(current_scores['Date'], current_scores['Player']))
            new_keys = set(zip(df_new['Date'], df_new['Player']))
            
            duplicates = existing_keys.intersection(new_keys)
            if duplicates:
                print(f"⚠️ Warning: {len(duplicates)} duplicate score entries found. Skipping them.")
                df_new = df_new[~df_new.apply(lambda x: (x['Date'], x['Player']) in duplicates, axis=1)]
        
        if not df_new.empty:
            current_scores = pd.concat([current_scores, df_new], ignore_index=True)
            print(f"✅ Added {len(df_new)} new scores.")
    
    # 2. Process Financials
    new_fin = data.get('financials', [])
    if new_fin:
        df_fin = pd.DataFrame(new_fin)
        df_fin['Date'] = date_str
        
        # Simple append for financials (allowing multiple entries per player per cat is okay, but usually unique)
        # We'll just append for now.
        current_financials = pd.concat([current_financials, df_fin], ignore_index=True)
        print(f"✅ Added {len(df_fin)} financial records.")

    # 3. Process Handicaps
    new_hcp = data.get('handicaps', [])
    if new_hcp:
        df_hcp = pd.DataFrame(new_hcp)
        df_hcp['Date'] = date_str
        
        if not current_handicaps.empty:
            existing_keys = set(zip(current_handicaps['Date'], current_handicaps['Player']))
            duplicates = set(zip(df_hcp['Date'], df_hcp['Player'])).intersection(existing_keys)
             
            if duplicates:
                 df_hcp = df_hcp[~df_hcp.apply(lambda x: (x['Date'], x['Player']) in duplicates, axis=1)]
        
        if not df_hcp.empty:
            current_handicaps = pd.concat([current_handicaps, df_hcp], ignore_index=True)
            print(f"✅ Added {len(df_hcp)} handicap records.")

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
