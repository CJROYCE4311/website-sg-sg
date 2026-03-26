import pandas as pd
import os
import json
import argparse
import sys
import subprocess
import shutil
import copy
from datetime import datetime

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
DB_DIR = os.path.join(PROJECT_ROOT, "data")
HISTORY_DIR = os.path.join(PROJECT_ROOT, "input", "history")

SCORES_FILE = os.path.join(DB_DIR, "scores.csv")
FINANCIALS_FILE = os.path.join(DB_DIR, "financials.csv")
HANDICAPS_FILE = os.path.join(DB_DIR, "handicaps.csv")
ALIASES_FILE = os.path.join(DB_DIR, "player_aliases.json")

# Validation constants
HOLE_COLS = [f'H{i}' for i in range(1, 19)]
MIN_HANDICAP = -10.0
MAX_HANDICAP = 54.0
MIN_GROSS_SCORE = 50
MAX_GROSS_SCORE = 150
BASE_SLOPE = 113
COURSE_SLOPE = 124
COURSE_RATING = 70.5
COURSE_PAR = 72
KNOWN_PARTIAL_SCORE_DATES = {"2025-01-04"}


def calculate_differential(gross_score):
    if pd.isna(gross_score):
        return pd.NA
    return round((float(gross_score) - COURSE_RATING) * BASE_SLOPE / COURSE_SLOPE, 1)


def calculate_course_handicap(index_value):
    if pd.isna(index_value):
        return pd.NA
    return round(float(index_value) * COURSE_SLOPE / BASE_SLOPE + (COURSE_RATING - COURSE_PAR), 1)


def calculate_handicap_index(course_handicap):
    if pd.isna(course_handicap):
        return pd.NA
    return round((float(course_handicap) - (COURSE_RATING - COURSE_PAR)) * BASE_SLOPE / COURSE_SLOPE, 1)


def clean_player_name(name):
    if name is None or pd.isna(name):
        return name
    return " ".join(str(name).split())


def load_player_aliases():
    if not os.path.exists(ALIASES_FILE):
        return {}

    with open(ALIASES_FILE, 'r') as f:
        raw_aliases = json.load(f)

    aliases = {}
    for alias, canonical in raw_aliases.items():
        clean_alias = clean_player_name(alias)
        clean_canonical = clean_player_name(canonical)
        if clean_alias and clean_canonical:
            aliases[clean_alias.casefold()] = clean_canonical
    return aliases


def canonicalize_player_name(name, aliases):
    cleaned = clean_player_name(name)
    if cleaned is None or pd.isna(cleaned):
        return cleaned
    return aliases.get(cleaned.casefold(), cleaned)


def normalize_player_fields(records, aliases, fields, rewrites, section):
    for record in records:
        for field in fields:
            if field not in record or record[field] is None:
                continue
            original = clean_player_name(record[field])
            canonical = canonicalize_player_name(original, aliases)
            record[field] = canonical
            if original != canonical:
                rewrites.append({
                    'section': section,
                    'field': field,
                    'from': original,
                    'to': canonical,
                })


def normalize_payload_names(data, aliases):
    normalized = copy.deepcopy(data)
    rewrites = []

    entries = normalized.get('update_batch', [normalized])
    for entry in entries:
        normalize_player_fields(entry.get('scores', []), aliases, ['Player', 'Partner'], rewrites, 'scores')
        normalize_player_fields(entry.get('financials', []), aliases, ['Player'], rewrites, 'financials')
        normalize_player_fields(entry.get('handicaps', []), aliases, ['Player'], rewrites, 'handicaps')

    unique_rewrites = []
    seen = set()
    for rewrite in rewrites:
        key = (rewrite['section'], rewrite['field'], rewrite['from'], rewrite['to'])
        if key in seen:
            continue
        seen.add(key)
        unique_rewrites.append(rewrite)
    return normalized, unique_rewrites


def ensure_handicap_columns(df):
    df = df.copy()

    if 'Handicap_Index' in df.columns:
        df['Handicap_Index'] = pd.to_numeric(df['Handicap_Index'], errors='coerce')
    if 'Course_Handicap' in df.columns:
        df['Course_Handicap'] = pd.to_numeric(df['Course_Handicap'], errors='coerce')

    if 'Course_Handicap' not in df.columns:
        df['Course_Handicap'] = df['Handicap_Index'].apply(calculate_course_handicap)
    elif 'Handicap_Index' in df.columns:
        missing_course = df['Course_Handicap'].isna() & df['Handicap_Index'].notna()
        df.loc[missing_course, 'Course_Handicap'] = df.loc[missing_course, 'Handicap_Index'].apply(calculate_course_handicap)

    return df


def ensure_scores_columns(df):
    df = df.copy()

    if 'Round_Handicap' in df.columns and 'Differential' not in df.columns:
        df = df.rename(columns={'Round_Handicap': 'Differential'})

    if 'Gross_Score' in df.columns:
        df['Gross_Score'] = pd.to_numeric(df['Gross_Score'], errors='coerce')
        df['Differential'] = df['Gross_Score'].apply(calculate_differential)
    elif 'Differential' in df.columns:
        df['Differential'] = pd.to_numeric(df['Differential'], errors='coerce')

    return df


def normalize_dataframe_player_names(df, aliases, fields, key_cols=None):
    if df.empty:
        return df

    normalized = df.copy()
    for field in fields:
        if field in normalized.columns:
            normalized[field] = normalized[field].apply(lambda value: canonicalize_player_name(value, aliases))

    if key_cols and set(key_cols).issubset(normalized.columns):
        normalized = normalized.drop_duplicates(subset=key_cols, keep='last').reset_index(drop=True)

    return normalized


def build_archive_label(data):
    """Return a stable archive label for single-date or batch payloads."""
    if 'update_batch' in data:
        dates = sorted({entry.get('date') for entry in data['update_batch'] if entry.get('date')})
        if not dates:
            return None
        if len(dates) == 1:
            return dates[0]
        return f"{dates[0]}_to_{dates[-1]}"
    return data.get('date')


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

    metadata = data.get('metadata', {})
    if not metadata:
        warnings.append(f"{date_str}: missing metadata block")
    else:
        for field in ['full_scorecard_available', 'handicap_list_available']:
            if field in metadata and not isinstance(metadata[field], bool):
                errors.append(f"{date_str}: metadata.{field} must be true/false")
            elif field not in metadata:
                warnings.append(f"{date_str}: metadata missing '{field}'")

        screenshots = metadata.get('screenshots')
        if screenshots is not None and not isinstance(screenshots, list):
            errors.append(f"{date_str}: metadata.screenshots must be a list when provided")

        approximations = metadata.get('approximations')
        if approximations is not None and not isinstance(approximations, list):
            errors.append(f"{date_str}: metadata.approximations must be a list when provided")

        source_notes = metadata.get('source_notes')
        if source_notes is not None and not isinstance(source_notes, (str, list)):
            errors.append(f"{date_str}: metadata.source_notes must be text or a list when provided")

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

        # Validate differential if explicitly provided
        differential = score.get('Differential')
        if differential is not None:
            expected_diff = calculate_differential(gross)
            if pd.notna(expected_diff) and round(float(differential), 1) != expected_diff:
                errors.append(f"{player}: Differential {differential} != expected {expected_diff}")

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
        course_hcp = hcp.get('Course_Handicap')
        if course_hcp is not None and (course_hcp < MIN_HANDICAP or course_hcp > MAX_HANDICAP):
            errors.append(f"Handicap entry {i}: course handicap {course_hcp} outside valid range")

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
    aliases = load_player_aliases()
    scores = pd.read_csv(SCORES_FILE) if os.path.exists(SCORES_FILE) else pd.DataFrame()
    financials = pd.read_csv(FINANCIALS_FILE) if os.path.exists(FINANCIALS_FILE) else pd.DataFrame()
    handicaps = pd.read_csv(HANDICAPS_FILE) if os.path.exists(HANDICAPS_FILE) else pd.DataFrame()
    if not scores.empty:
        scores = ensure_scores_columns(scores)
        scores = normalize_dataframe_player_names(scores, aliases, ['Player', 'Partner'], key_cols=['Date', 'Player'])
    if not handicaps.empty:
        handicaps = ensure_handicap_columns(handicaps)
        handicaps = normalize_dataframe_player_names(handicaps, aliases, ['Player'], key_cols=['Date', 'Player'])
    if not financials.empty:
        financials = normalize_dataframe_player_names(financials, aliases, ['Player'], key_cols=['Date', 'Player', 'Category'])
    return scores, financials, handicaps

def sort_canonical_tables(scores, financials, handicaps):
    if not scores.empty:
        scores = scores.sort_values(['Date', 'Player']).reset_index(drop=True)
    if not financials.empty:
        financials = financials.sort_values(['Date', 'Player', 'Category']).reset_index(drop=True)
    if not handicaps.empty:
        handicaps = handicaps.sort_values(['Date', 'Player']).reset_index(drop=True)
    return scores, financials, handicaps


def save_db(scores, financials, handicaps):
    aliases = load_player_aliases()
    scores = ensure_scores_columns(scores)
    handicaps = ensure_handicap_columns(handicaps)
    scores = normalize_dataframe_player_names(scores, aliases, ['Player', 'Partner'], key_cols=['Date', 'Player'])
    financials = normalize_dataframe_player_names(financials, aliases, ['Player'], key_cols=['Date', 'Player', 'Category'])
    handicaps = normalize_dataframe_player_names(handicaps, aliases, ['Player'], key_cols=['Date', 'Player'])
    scores, financials, handicaps = sort_canonical_tables(scores, financials, handicaps)
    scores.to_csv(SCORES_FILE, index=False)
    financials.to_csv(FINANCIALS_FILE, index=False)
    handicaps.to_csv(HANDICAPS_FILE, index=False)
    print("✅ Database saved successfully.")


def duplicate_key_issues(df, key_cols, label):
    if df.empty:
        return []

    missing_cols = [col for col in key_cols if col not in df.columns]
    if missing_cols:
        return [f"{label}: missing key columns {missing_cols}"]

    duplicate_rows = df[df.duplicated(subset=key_cols, keep=False)]
    if duplicate_rows.empty:
        return []

    sample_keys = (
        duplicate_rows[key_cols]
        .drop_duplicates()
        .head(5)
        .to_dict('records')
    )
    return [f"{label}: duplicate keys detected for {sample_keys}"]


def validate_canonical_state(scores, financials, handicaps):
    issues = []
    issues.extend(duplicate_key_issues(scores, ['Date', 'Player'], 'scores'))
    issues.extend(duplicate_key_issues(financials, ['Date', 'Player', 'Category'], 'financials'))
    issues.extend(duplicate_key_issues(handicaps, ['Date', 'Player'], 'handicaps'))
    return issues


def build_canonical_audit(scores, financials, handicaps):
    issues = validate_canonical_state(scores, financials, handicaps)

    score_keys = (
        scores[['Date', 'Player']].drop_duplicates()
        if not scores.empty and {'Date', 'Player'}.issubset(scores.columns)
        else pd.DataFrame(columns=['Date', 'Player'])
    )
    handicap_keys = (
        handicaps[['Date', 'Player']].drop_duplicates()
        if not handicaps.empty and {'Date', 'Player'}.issubset(handicaps.columns)
        else pd.DataFrame(columns=['Date', 'Player'])
    )

    missing_snapshots = score_keys.merge(
        handicap_keys,
        on=['Date', 'Player'],
        how='left',
        indicator=True,
    )
    missing_snapshots = missing_snapshots[missing_snapshots['_merge'] == 'left_only'][['Date', 'Player']]
    missing_snapshots = missing_snapshots.sort_values(['Date', 'Player']).reset_index(drop=True)

    orphan_snapshots = handicap_keys.merge(
        score_keys,
        on=['Date', 'Player'],
        how='left',
        indicator=True,
    )
    orphan_snapshots = orphan_snapshots[orphan_snapshots['_merge'] == 'left_only'][['Date', 'Player']]
    orphan_snapshots = orphan_snapshots.sort_values(['Date', 'Player']).reset_index(drop=True)

    financial_keys = (
        financials[['Date', 'Player']].drop_duplicates()
        if not financials.empty and {'Date', 'Player'}.issubset(financials.columns)
        else pd.DataFrame(columns=['Date', 'Player'])
    )
    orphan_financials = financial_keys.merge(
        score_keys,
        on=['Date', 'Player'],
        how='left',
        indicator=True,
    )
    orphan_financials = orphan_financials[orphan_financials['_merge'] == 'left_only'][['Date', 'Player']]
    orphan_financials = orphan_financials.sort_values(['Date', 'Player']).reset_index(drop=True)

    incomplete_report_rows = len(missing_snapshots)
    return {
        'duplicate_issues': issues,
        'missing_snapshots': missing_snapshots,
        'orphan_snapshots': orphan_snapshots,
        'orphan_financials': orphan_financials,
        'incomplete_report_rows': incomplete_report_rows,
    }


def print_canonical_audit(audit):
    print("\n📋 Canonical Data Audit")
    print(f"   - Duplicate key issues: {len(audit['duplicate_issues'])}")
    print(f"   - Scores missing handicap snapshots: {len(audit['missing_snapshots'])}")
    print(f"   - Handicap snapshots without score rows: {len(audit['orphan_snapshots'])}")
    print(f"   - Financial rows without score rows: {len(audit['orphan_financials'])}")
    print(f"   - Report rows with blank handicap-dependent fields: {audit['incomplete_report_rows']}")

    if audit['duplicate_issues']:
        print("   Duplicate details:")
        for issue in audit['duplicate_issues']:
            print(f"     * {issue}")

    if not audit['missing_snapshots'].empty:
        print("   Missing snapshot details:")
        for row in audit['missing_snapshots'].itertuples(index=False):
            print(f"     * {row.Date} | {row.Player}")

    if not audit['orphan_snapshots'].empty:
        sample = audit['orphan_snapshots'].head(25)
        print("   Review-only handicap snapshots without score rows:")
        for row in sample.itertuples(index=False):
            print(f"     * {row.Date} | {row.Player}")
        if len(audit['orphan_snapshots']) > len(sample):
            print(f"     * ... and {len(audit['orphan_snapshots']) - len(sample)} more")

    if not audit['orphan_financials'].empty:
        sample = audit['orphan_financials'].head(25)
        print("   Financial rows without score rows:")
        for row in sample.itertuples(index=False):
            print(f"     * {row.Date} | {row.Player}")
        if len(audit['orphan_financials']) > len(sample):
            print(f"     * ... and {len(audit['orphan_financials']) - len(sample)} more")


def audit_has_fatal_issues(audit):
    return (
        bool(audit['duplicate_issues'])
        or not audit['missing_snapshots'].empty
        or not audit['orphan_snapshots'].empty
    )

def get_handicap_review_flags(data, current_handicaps):
    review_flags = []
    handicap_entries = data.get('handicaps', [])

    if current_handicaps.empty or not handicap_entries:
        return review_flags

    for entry in handicap_entries:
        player = entry.get('Player')
        index_value = entry.get('Handicap_Index')
        if player is None or index_value is None:
            continue

        history = current_handicaps[current_handicaps['Player'] == player]['Handicap_Index'].dropna()
        if len(history) < 2:
            continue

        hist_mean = history.mean()
        hist_std = history.std(ddof=1)
        if pd.isna(hist_std) or hist_std == 0:
            continue

        z_score = (float(index_value) - hist_mean) / hist_std
        if abs(z_score) > 1:
            review_flags.append({
                'Player': player,
                'new_index': float(index_value),
                'mean': round(float(hist_mean), 2),
                'std': round(float(hist_std), 2),
                'z_score': round(float(z_score), 2),
            })

    return review_flags

def upsert_financials(current_financials, df_fin):
    if df_fin.empty:
        return current_financials, 0, 0, 0

    key_cols = ['Date', 'Player', 'Category']
    incoming = df_fin.drop_duplicates(subset=key_cols, keep='last').reset_index(drop=True)
    payload_duplicates = len(df_fin) - len(incoming)

    if current_financials.empty:
        return incoming, len(incoming), 0, payload_duplicates

    current_financials = current_financials.copy()
    all_columns = list(current_financials.columns)
    for col in incoming.columns:
        if col not in all_columns:
            all_columns.append(col)

    current_financials = current_financials.reindex(columns=all_columns)
    incoming = incoming.reindex(columns=all_columns)

    current_keys = set(map(tuple, current_financials[key_cols].astype(str).itertuples(index=False, name=None)))
    incoming_keys = set(map(tuple, incoming[key_cols].astype(str).itertuples(index=False, name=None)))

    added = len(incoming_keys - current_keys)
    updated = len(incoming_keys & current_keys)

    combined = pd.concat([current_financials, incoming], ignore_index=True)
    combined = combined.drop_duplicates(subset=key_cols, keep='last').reset_index(drop=True)
    return combined, added, updated, payload_duplicates


def upsert_handicaps(current_handicaps, df_hcp):
    if df_hcp.empty:
        return current_handicaps, 0, 0, 0

    key_cols = ['Date', 'Player']
    incoming = df_hcp.drop_duplicates(subset=key_cols, keep='last').reset_index(drop=True)
    payload_duplicates = len(df_hcp) - len(incoming)

    if current_handicaps.empty:
        return incoming, len(incoming), 0, payload_duplicates

    current_handicaps = current_handicaps.copy()
    all_columns = list(current_handicaps.columns)
    for col in incoming.columns:
        if col not in all_columns:
            all_columns.append(col)

    current_handicaps = current_handicaps.reindex(columns=all_columns)
    incoming = incoming.reindex(columns=all_columns)

    current_keys = set(map(tuple, current_handicaps[key_cols].astype(str).itertuples(index=False, name=None)))
    incoming_keys = set(map(tuple, incoming[key_cols].astype(str).itertuples(index=False, name=None)))

    added = len(incoming_keys - current_keys)
    updated = len(incoming_keys & current_keys)

    combined = pd.concat([current_handicaps, incoming], ignore_index=True)
    combined = combined.drop_duplicates(subset=key_cols, keep='last').reset_index(drop=True)
    return combined, added, updated, payload_duplicates


def missing_score_snapshot_players(date_str, score_df, current_handicaps, incoming_handicaps=None):
    if score_df.empty:
        return []

    available = current_handicaps.copy()
    if incoming_handicaps is not None and not incoming_handicaps.empty:
        available = pd.concat([available, incoming_handicaps], ignore_index=True)
        available = available.drop_duplicates(subset=['Date', 'Player'], keep='last')

    day_snapshots = available[available['Date'].astype(str) == str(date_str)]
    available_players = set(day_snapshots['Player'].astype(str))
    score_players = set(score_df['Player'].astype(str))
    return sorted(score_players - available_players)

def process_entry(data, current_scores, current_financials, current_handicaps, allow_incomplete=False):
    date_str = data.get('date')
    if not date_str:
        print("❌ Error: Entry missing 'date' field.")
        return current_scores, current_financials, current_handicaps, False
        
    print(f"📅 Processing Date: {date_str}")
    
    # 1. Process Scores
    new_scores = data.get('scores', [])
    df_new = pd.DataFrame()
    score_snapshot_df = pd.DataFrame()
    if new_scores:
        df_new = pd.DataFrame(new_scores)
        df_new['Date'] = date_str
        df_new = ensure_scores_columns(df_new)
        if 'Round_Handicap' in df_new.columns:
            df_new = df_new.drop(columns=['Round_Handicap'])
        score_snapshot_df = df_new.copy()
        
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
        current_financials, added_financials, updated_financials, payload_duplicates = upsert_financials(current_financials, df_fin)
        print(
            "   ✅ Financials: Added {added} new, updated {updated} existing, collapsed {collapsed} duplicate payload rows.".format(
                added=added_financials,
                updated=updated_financials,
                collapsed=payload_duplicates,
            )
        )

    # 3. Process Handicaps
    new_hcp = data.get('handicaps', [])
    df_hcp = pd.DataFrame()
    if new_hcp:
        df_hcp = pd.DataFrame(new_hcp)
        df_hcp['Date'] = date_str
        df_hcp = ensure_handicap_columns(df_hcp)
        current_handicaps, added_hcp, updated_hcp, payload_duplicates = upsert_handicaps(current_handicaps, df_hcp)
        print(
            "   ✅ Handicaps: Added {added} new, updated {updated} existing, collapsed {collapsed} duplicate payload rows.".format(
                added=added_hcp,
                updated=updated_hcp,
                collapsed=payload_duplicates,
            )
        )

    missing_players = missing_score_snapshot_players(date_str, score_snapshot_df, current_handicaps)
    if missing_players:
        print("❌ Missing handicap snapshots for scored players:")
        for player in missing_players:
            print(f"   - {player}")
        if not allow_incomplete:
            print("\n❌ Aborting before writing scores without matching handicap snapshots.")
            return current_scores, current_financials, current_handicaps, False
        print("\n⚠️ Continuing because --allow-incomplete was provided.")
            
    return current_scores, current_financials, current_handicaps, True

def ingest(json_file, skip_validation=False, skip_archive=False, skip_site_update=False, dry_run=False, allow_incomplete=False):
    print(f"📥 Ingesting {json_file}...")

    with open(json_file, 'r') as f:
        data = json.load(f)

    player_aliases = load_player_aliases()
    data, alias_rewrites = normalize_payload_names(data, player_aliases)
    if alias_rewrites:
        print("🪪 Normalized player aliases:")
        for rewrite in alias_rewrites:
            print(
                "   - {section}.{field}: {from_name} -> {to_name}".format(
                    section=rewrite['section'],
                    field=rewrite['field'],
                    from_name=rewrite['from'],
                    to_name=rewrite['to'],
                )
            )

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

    if 'update_batch' in data:
        handicap_flags = []
        for entry in data['update_batch']:
            handicap_flags.extend(get_handicap_review_flags(entry, current_handicaps))
    else:
        handicap_flags = get_handicap_review_flags(data, current_handicaps)

    if handicap_flags:
        print("🔎 Handicap review: values more than 1 SD from historical mean")
        for flag in sorted(handicap_flags, key=lambda item: abs(item['z_score']), reverse=True):
            print(
                "   - {Player}: new {new_index:.1f}, mean {mean:.2f}, std {std:.2f}, z {z_score:+.2f}".format(
                    **flag
                )
            )

    entries = data['update_batch'] if 'update_batch' in data else [data]
    approximation_notes = []
    for entry in entries:
        metadata = entry.get('metadata') or {}
        for note in metadata.get('approximations', []) or []:
            approximation_notes.append((entry.get('date'), note))
    if approximation_notes:
        print("📝 Approximation notes:")
        for date_str, note in approximation_notes:
            print(f"   - {date_str}: {note}")

    archive_label = build_archive_label(data)

    if 'update_batch' in data:
        print(f"📦 Batch Update Detected: {len(data['update_batch'])} entries.")
        for entry in data['update_batch']:
            current_scores, current_financials, current_handicaps, processed = process_entry(
                entry, current_scores, current_financials, current_handicaps, allow_incomplete=allow_incomplete
            )
            if not processed:
                return False
    else:
        current_scores, current_financials, current_handicaps, processed = process_entry(
            data, current_scores, current_financials, current_handicaps, allow_incomplete=allow_incomplete
        )
        if not processed:
            return False

    canonical_issues = validate_canonical_state(current_scores, current_financials, current_handicaps)
    if canonical_issues:
        print("❌ Post-ingest validation failed:")
        for issue in canonical_issues:
            print(f"   - {issue}")
        print("\n❌ Aborting before writing canonical files.")
        return False

    audit = build_canonical_audit(current_scores, current_financials, current_handicaps)
    print_canonical_audit(audit)
    if audit_has_fatal_issues(audit) and not allow_incomplete:
        print("\n❌ Aborting before writing canonical files because the audit found blocking issues.")
        return False
    if audit_has_fatal_issues(audit) and allow_incomplete:
        print("\n⚠️ Audit found blocking issues, but continuing because --allow-incomplete was provided.")

    if dry_run:
        print("🧪 Dry run complete. No CSVs, archives, or website files were modified.")
        return True

    save_db(current_scores, current_financials, current_handicaps)

    # Archive JSON
    if not skip_archive and archive_label:
        archive_json(json_file, archive_label)

    # Trigger Site Update
    if not skip_site_update:
        print("\n🔄 Triggering Site Update...")
        venv_python = os.path.join(PROJECT_ROOT, "venv", "bin", "python")
        if not os.path.exists(venv_python):
            venv_python = "python"  # Fallback

        subprocess.run([venv_python, os.path.join(SCRIPT_DIR, "update_site.py")], check=True)
    else:
        print("\nℹ️ Skipped site update.")
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest new tournament data.")
    parser.add_argument("input_file", help="Path to JSON file containing new data.")
    parser.add_argument("--skip-validation", action="store_true", help="Skip data validation")
    parser.add_argument("--skip-archive", action="store_true", help="Skip JSON archiving")
    parser.add_argument("--skip-site-update", action="store_true", help="Skip regenerating website files")
    parser.add_argument("--dry-run", action="store_true", help="Validate and simulate ingestion without writing files")
    parser.add_argument("--allow-incomplete", action="store_true",
                        help="Allow writes even when score/handicap coverage audit is incomplete")
    args = parser.parse_args()

    if not os.path.exists(args.input_file):
        print(f"❌ Input file not found: {args.input_file}")
        sys.exit(1)

    success = ingest(
        args.input_file,
        skip_validation=args.skip_validation,
        skip_archive=args.skip_archive,
        skip_site_update=args.skip_site_update,
        dry_run=args.dry_run,
        allow_incomplete=args.allow_incomplete,
    )
    sys.exit(0 if success else 1)
