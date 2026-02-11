import pandas as pd
import os
import json
import argparse
import sys
import subprocess
import shutil
from datetime import datetime

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
DB_DIR = os.path.join(PROJECT_ROOT, "data")
HISTORY_DIR = os.path.join(PROJECT_ROOT, "input", "history")

SCORES_FILE = os.path.join(DB_DIR, "scores.csv")
FINANCIALS_FILE = os.path.join(DB_DIR, "financials.csv")
HANDICAPS_FILE = os.path.join(DB_DIR, "handicaps.csv")

# Validation constants
HOLE_COLS = [f'H{i}' for i in range(1, 19)]
MIN_HANDICAP = -10.0
MAX_HANDICAP = 54.0
MIN_GROSS_SCORE = 50
MAX_GROSS_SCORE = 150


def validate_data(data):
    """Validate tournament data before ingestion. Returns (is_valid, errors)."""
    errors = []
    warnings = []

    date_str = data.get('date')
    if not date_str:
        errors.append("Missing 'date' field")
        return False, errors, warnings

    # Validate date format
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        errors.append(f"Invalid date format: {date_str} (expected YYYY-MM-DD)")

    # Validate scores
    scores = data.get('scores', [])
    seen_players = set()

    for i, score in enumerate(scores):
        player = score.get('Player', f'Unknown-{i}')

        # Check for duplicate players
        if player in seen_players:
            errors.append(f"Duplicate player in scores: {player}")
        seen_players.add(player)

        # Check required fields
        if 'Player' not in score:
            errors.append(f"Score entry {i}: missing 'Player' field")
        if 'Gross_Score' not in score:
            errors.append(f"Score entry {i} ({player}): missing 'Gross_Score' field")

        # Validate gross score matches sum of holes
        hole_sum = sum(score.get(h, 0) or 0 for h in HOLE_COLS)
        gross = score.get('Gross_Score', 0) or 0

        if hole_sum > 0 and gross > 0 and hole_sum != gross:
            errors.append(f"{player}: Gross_Score ({gross}) != sum of holes ({hole_sum})")

        # Validate gross score range
        if gross > 0 and (gross < MIN_GROSS_SCORE or gross > MAX_GROSS_SCORE):
            warnings.append(f"{player}: Unusual gross score: {gross}")

        # Validate handicap range
        hcp = score.get('Round_Handicap')
        if hcp is not None and (hcp < MIN_HANDICAP or hcp > MAX_HANDICAP):
            errors.append(f"{player}: Handicap {hcp} outside valid range ({MIN_HANDICAP} to {MAX_HANDICAP})")

    # Validate financials
    financials = data.get('financials', [])
    valid_categories = {'BestBall', 'Quota', 'NetMedal', 'GrossSkins', 'NetSkins'}

    for i, fin in enumerate(financials):
        if 'Player' not in fin:
            errors.append(f"Financial entry {i}: missing 'Player' field")
        if 'Category' not in fin:
            errors.append(f"Financial entry {i}: missing 'Category' field")
        elif fin['Category'] not in valid_categories:
            warnings.append(f"Financial entry {i}: unknown category '{fin['Category']}'")
        if 'Amount' not in fin:
            errors.append(f"Financial entry {i}: missing 'Amount' field")
        elif fin['Amount'] < 0:
            errors.append(f"Financial entry {i}: negative amount {fin['Amount']}")

    # Validate handicaps
    handicaps = data.get('handicaps', [])
    for i, hcp in enumerate(handicaps):
        if 'Player' not in hcp:
            errors.append(f"Handicap entry {i}: missing 'Player' field")
        if 'Handicap_Index' not in hcp:
            errors.append(f"Handicap entry {i}: missing 'Handicap_Index' field")
        else:
            idx = hcp['Handicap_Index']
            if idx < MIN_HANDICAP or idx > MAX_HANDICAP:
                errors.append(f"Handicap entry {i}: index {idx} outside valid range")

    # Print warnings
    for w in warnings:
        print(f"   ⚠️  Warning: {w}")

    return len(errors) == 0, errors, warnings


def archive_json(json_file, date_str):
    """Archive the JSON file to input/history/ folder."""
    os.makedirs(HISTORY_DIR, exist_ok=True)

    # Create filename with date
    archive_name = f"{date_str}.json"
    archive_path = os.path.join(HISTORY_DIR, archive_name)

    # If file already exists, add a suffix
    counter = 1
    while os.path.exists(archive_path):
        archive_name = f"{date_str}_{counter}.json"
        archive_path = os.path.join(HISTORY_DIR, archive_name)
        counter += 1

    shutil.copy2(json_file, archive_path)
    print(f"📁 Archived JSON to: input/history/{archive_name}")

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

def ingest(json_file, skip_validation=False, skip_archive=False):
    print(f"📥 Ingesting {json_file}...")

    with open(json_file, 'r') as f:
        data = json.load(f)

    # Validation
    if not skip_validation:
        print("🔍 Validating data...")
        if 'update_batch' in data:
            all_valid = True
            for entry in data['update_batch']:
                is_valid, errors, _ = validate_data(entry)
                if not is_valid:
                    all_valid = False
                    print(f"❌ Validation failed for {entry.get('date', 'unknown date')}:")
                    for e in errors:
                        print(f"   - {e}")
            if not all_valid:
                print("\n❌ Aborting due to validation errors. Fix the data and retry.")
                return False
        else:
            is_valid, errors, _ = validate_data(data)
            if not is_valid:
                print("❌ Validation failed:")
                for e in errors:
                    print(f"   - {e}")
                print("\n❌ Aborting due to validation errors. Fix the data and retry.")
                return False
        print("   ✅ Validation passed")

    current_scores, current_financials, current_handicaps = load_db()

    # Track date for archiving
    archive_date = None

    if 'update_batch' in data:
        print(f"📦 Batch Update Detected: {len(data['update_batch'])} entries.")
        for entry in data['update_batch']:
            current_scores, current_financials, current_handicaps = process_entry(
                entry, current_scores, current_financials, current_handicaps
            )
            archive_date = entry.get('date', archive_date)
    else:
        current_scores, current_financials, current_handicaps = process_entry(
            data, current_scores, current_financials, current_handicaps
        )
        archive_date = data.get('date')

    save_db(current_scores, current_financials, current_handicaps)

    # Archive JSON
    if not skip_archive and archive_date:
        archive_json(json_file, archive_date)

    # Trigger Site Update
    print("\n🔄 Triggering Site Update...")
    venv_python = os.path.join(PROJECT_ROOT, "venv", "bin", "python")
    if not os.path.exists(venv_python):
        venv_python = "python"  # Fallback

    subprocess.run([venv_python, os.path.join(SCRIPT_DIR, "update_site.py")])
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest new tournament data.")
    parser.add_argument("input_file", help="Path to JSON file containing new data.")
    parser.add_argument("--skip-validation", action="store_true", help="Skip data validation")
    parser.add_argument("--skip-archive", action="store_true", help="Skip JSON archiving")
    args = parser.parse_args()

    if not os.path.exists(args.input_file):
        print(f"❌ Input file not found: {args.input_file}")
        sys.exit(1)

    success = ingest(args.input_file, args.skip_validation, args.skip_archive)
    sys.exit(0 if success else 1)
