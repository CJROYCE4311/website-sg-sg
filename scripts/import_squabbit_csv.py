#!/usr/bin/env python3
"""Convert Squabbit tournament CSV exports into reviewed ingest JSON.

The Squabbit export is the raw source layer. This script keeps the current
canonical CSV model as the write target by producing the same JSON payload that
scripts/process_tournament.py already validates and ingests.
"""

import argparse
import csv
import json
import os
import re
from collections import defaultdict
from datetime import datetime

import pandas as pd


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
DEFAULT_IDENTITY_MAP = os.path.join(PROJECT_ROOT, "input", "identity", "squabbit_players.csv")
DEFAULT_OUTPUT = os.path.join(PROJECT_ROOT, "input", "tournament_data.from_squabbit.json")
DEFAULT_REPORT_JSON = os.path.join(PROJECT_ROOT, "input", "squabbit_reconciliation_report.json")
DEFAULT_REPORT_MD = os.path.join(PROJECT_ROOT, "input", "squabbit_reconciliation_report.md")

SCORES_FILE = os.path.join(DATA_DIR, "scores.csv")
FINANCIALS_FILE = os.path.join(DATA_DIR, "financials.csv")
HANDICAPS_FILE = os.path.join(DATA_DIR, "handicaps.csv")
ALIASES_FILE = os.path.join(DATA_DIR, "player_aliases.json")

HOLE_COLS = [f"H{i}" for i in range(1, 19)]
BASE_SLOPE = 113
COURSE_SLOPE = 124
COURSE_RATING = 70.5
COURSE_PAR = 72
TEAM_BUY_IN = 20.0
OPTIONAL_GAME_BUY_IN = 10.0
PAYOUT_PERCENTS = [0.60, 0.30, 0.10]


def clean_player_name(name):
    if name is None:
        return ""
    cleaned = str(name)
    cleaned = re.sub(r'\s*"[^"]*"\s*', " ", cleaned)
    cleaned = re.sub(r"\s+Captain\s*$", "", cleaned, flags=re.IGNORECASE)
    return " ".join(cleaned.split())


def parse_money(value):
    raw = str(value or "").strip().replace("$", "").replace(",", "")
    if raw in {"", "-"}:
        return 0.0
    return float(raw)


def parse_handicap(value):
    raw = str(value or "").strip()
    if not raw or raw.lower() == "not set":
        return None
    if raw.startswith("+"):
        return -float(raw[1:])
    return float(raw)


def parse_signed_score(value):
    raw = str(value or "").strip()
    if raw in {"", "E"}:
        return 0
    if "thru" in raw:
        return None
    return int(raw)


def parse_skin_count(value):
    raw = str(value or "").strip()
    if raw in {"", "-"}:
        return 0
    return int(raw)


def format_amount(value):
    rounded = round(float(value), 2)
    if abs(rounded - round(rounded)) < 0.005:
        return float(round(rounded))
    return rounded


def calculate_differential(gross_score):
    return round((float(gross_score) - COURSE_RATING) * BASE_SLOPE / COURSE_SLOPE, 1)


def calculate_course_handicap(index_value):
    return round(float(index_value) * COURSE_SLOPE / BASE_SLOPE + (COURSE_RATING - COURSE_PAR), 1)


def load_aliases():
    if not os.path.exists(ALIASES_FILE):
        return {}
    with open(ALIASES_FILE, "r") as input_file:
        raw_aliases = json.load(input_file)
    return {
        clean_player_name(alias).casefold(): clean_player_name(canonical)
        for alias, canonical in raw_aliases.items()
        if clean_player_name(alias) and clean_player_name(canonical)
    }


def read_csv_rows(path):
    with open(path, newline="") as input_file:
        return list(csv.reader(input_file))


def first_nonblank_row(rows):
    for row in rows:
        if row and any(cell.strip() for cell in row):
            return row
    raise ValueError("CSV does not contain any nonblank rows")


def find_section(rows, title, start=0):
    for idx in range(start, len(rows)):
        row = rows[idx]
        if row and len([cell for cell in row if cell.strip()]) == 1 and row[0].strip() == title:
            return idx
    return None


def iter_summary_sections(rows, stop_idx):
    idx = 0
    while idx < stop_idx:
        row = rows[idx]
        if not row or not any(cell.strip() for cell in row):
            idx += 1
            continue
        if len([cell for cell in row if cell.strip()]) == 1 and idx + 1 < stop_idx:
            title = row[0].strip()
            header = rows[idx + 1]
            data = []
            cursor = idx + 2
            while cursor < stop_idx and rows[cursor] and any(cell.strip() for cell in rows[cursor]):
                data.append(rows[cursor])
                cursor += 1
            yield {
                "title": title,
                "header": header,
                "data": data,
                "line": idx + 1,
            }
            idx = cursor
        else:
            idx += 1


def load_identity_map(path):
    if not os.path.exists(path):
        return {}
    with open(path, newline="") as input_file:
        reader = csv.DictReader(input_file)
        return {
            row["WHS_ID"]: row
            for row in reader
            if row.get("WHS_ID")
        }


def write_identity_map(path, identity_map):
    if not identity_map:
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fieldnames = [
        "WHS_ID",
        "Canonical_Name",
        "Latest_Squabbit_Name",
        "First_Seen",
        "Last_Seen",
        "Source_File",
        "Notes",
    ]
    rows = sorted(identity_map.values(), key=lambda row: (row.get("Canonical_Name", ""), row.get("WHS_ID", "")))
    with open(path, "w", newline="") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def load_canonical_names():
    names = set()
    for path, columns in [
        (SCORES_FILE, ["Player", "Partner"]),
        (FINANCIALS_FILE, ["Player"]),
        (HANDICAPS_FILE, ["Player"]),
    ]:
        if not os.path.exists(path):
            continue
        df = pd.read_csv(path)
        for column in columns:
            if column in df.columns:
                names.update(clean_player_name(value) for value in df[column].dropna())
    return {name.casefold(): name for name in names if name}


def canonicalize_name(raw_name, aliases, canonical_case_map, whs_id=None, identity_map=None):
    latest_name = " ".join(str(raw_name or "").split())
    cleaned = clean_player_name(latest_name)
    if not cleaned:
        return cleaned

    if whs_id and identity_map and whs_id in identity_map:
        mapped = clean_player_name(identity_map[whs_id].get("Canonical_Name"))
        if mapped:
            return mapped

    alias_match = aliases.get(cleaned.casefold())
    if alias_match:
        return alias_match

    case_match = canonical_case_map.get(cleaned.casefold())
    if case_match:
        return case_match

    return cleaned


def parse_players(rows, aliases, canonical_case_map, identity_map, source_file, reports):
    players_idx = find_section(rows, "Players")
    if players_idx is None:
        raise ValueError("Missing Players section")

    header = rows[players_idx + 1]
    players = []
    cursor = players_idx + 2
    while cursor < len(rows) and rows[cursor] and any(cell.strip() for cell in rows[cursor]):
        raw = dict(zip(header, rows[cursor]))
        whs_id = raw.get("WHS Id", "").strip()
        raw_name = raw.get("Name", "")
        canonical = canonicalize_name(raw_name, aliases, canonical_case_map, whs_id, identity_map)
        index_value = parse_handicap(raw.get("HDCP"))
        player = {
            "Raw_Name": " ".join(str(raw_name).split()),
            "Player": canonical,
            "WHS_ID": whs_id,
            "Handicap_Index": index_value,
            "Course_Handicap": calculate_course_handicap(index_value) if index_value is not None else None,
            "Total_Fees": parse_money(raw.get("Total fees")),
            "Won": parse_money(raw.get("Won")),
        }
        players.append(player)

        if whs_id:
            existing = identity_map.get(whs_id)
            if existing and existing.get("Canonical_Name") and existing["Canonical_Name"] != canonical:
                reports["identity_conflicts"].append({
                    "whs_id": whs_id,
                    "existing": existing["Canonical_Name"],
                    "incoming": canonical,
                    "latest_squabbit_name": player["Raw_Name"],
                })
                canonical = existing["Canonical_Name"]
                player["Player"] = canonical
            identity_map[whs_id] = {
                "WHS_ID": whs_id,
                "Canonical_Name": canonical,
                "Latest_Squabbit_Name": player["Raw_Name"],
                "First_Seen": existing.get("First_Seen", "") if existing else "",
                "Last_Seen": "",
                "Source_File": source_file,
                "Notes": existing.get("Notes", "") if existing else "",
            }
        if player["Raw_Name"] != player["Player"]:
            reports["name_rewrites"].append({
                "from": player["Raw_Name"],
                "to": player["Player"],
                "whs_id": whs_id,
            })
        cursor += 1

    return players


def update_identity_seen_dates(identity_map, date_str, seen_whs_ids):
    for whs_id in seen_whs_ids:
        row = identity_map.get(whs_id)
        if not row:
            continue
        if not row.get("First_Seen") or date_str < row["First_Seen"]:
            row["First_Seen"] = date_str
        if not row.get("Last_Seen") or date_str > row["Last_Seen"]:
            row["Last_Seen"] = date_str


def rank_labels(items, value_key="rank_value", key_field="key"):
    labels = {}
    position = 1
    idx = 0
    ranked = [item for item in items if item.get(value_key) is not None]
    while idx < len(ranked):
        value = ranked[idx][value_key]
        next_idx = idx + 1
        while next_idx < len(ranked) and ranked[next_idx][value_key] == value:
            next_idx += 1
        label = f"T{position}" if next_idx - idx > 1 else str(position)
        for item in ranked[idx:next_idx]:
            labels[item[key_field]] = label
        position += next_idx - idx
        idx = next_idx
    return labels


def payout_by_rank(items, pool, key_field="key"):
    payouts = defaultdict(float)
    position = 1
    idx = 0
    ranked = [item for item in items if item.get("rank_value") is not None]
    while idx < len(ranked):
        value = ranked[idx]["rank_value"]
        next_idx = idx + 1
        while next_idx < len(ranked) and ranked[next_idx]["rank_value"] == value:
            next_idx += 1
        start = position - 1
        end = min(start + (next_idx - idx), len(PAYOUT_PERCENTS))
        group_pool = sum(PAYOUT_PERCENTS[start:end]) * pool
        if group_pool:
            share = group_pool / (next_idx - idx)
            for item in ranked[idx:next_idx]:
                payouts[item[key_field]] += share
        position += next_idx - idx
        idx = next_idx
    return payouts


def simple_items(section, player_map, score_parser=parse_signed_score):
    items = []
    for row in section["data"]:
        if not row or not row[0].strip():
            continue
        player = player_map.get(clean_player_name(row[0]), clean_player_name(row[0]))
        items.append({
            "key": player,
            "Player": player,
            "rank_value": score_parser(row[2]),
            "raw": row,
        })
    return items


def parse_team_section(section, player_map):
    teams = []
    current = None
    occurrence = 0
    for row in section["data"]:
        if row[0].strip():
            occurrence += 1
            current = {
                "key": f"{row[0].strip()}#{occurrence}",
                "label": row[0].strip(),
                "rank_value": parse_signed_score(row[2]),
                "players": [],
            }
            teams.append(current)
        elif current and len(row) > 1 and row[1].strip():
            current["players"].append(player_map.get(clean_player_name(row[1]), clean_player_name(row[1])))
    return teams


def parse_scorecards(rows, player_map, partners, team_ranks, individual_ranks):
    scores = []
    labels_by_player = defaultdict(list)
    cursor = 0
    while cursor < len(rows):
        row = rows[cursor]
        if len(row) > 23 and row[0].strip() and len(row) > 1 and row[1].endswith("tee"):
            player = player_map.get(clean_player_name(row[0]), clean_player_name(row[0]))
            holes = [int(value) for value in row[3:12] + row[13:22]]
            gross_score = int(row[23])
            record = {
                "Player": player,
                **{f"H{idx + 1}": holes[idx] for idx in range(18)},
                "Gross_Score": gross_score,
                "Partner": partners.get(player, ""),
                "Team_Rank": team_ranks.get(player, ""),
                "Individual_Rank": individual_ranks.get(player, ""),
            }
            scores.append(record)

            cursor += 1
            while cursor < len(rows):
                game_row = rows[cursor]
                if not game_row or not any(cell.strip() for cell in game_row):
                    break
                if len(game_row) > 23 and game_row[0].strip() and len(game_row) > 1 and game_row[1].endswith("tee"):
                    cursor -= 1
                    break
                if len(game_row) > 1 and game_row[1].strip():
                    labels_by_player[player].append(game_row[1].strip())
                cursor += 1
        cursor += 1
    return scores, labels_by_player


def build_financials(players, team_category, teams, team_payouts, net_skins_section, gross_skins_section, player_map):
    category_amounts = defaultdict(float)
    won_by_player = {player["Player"]: player["Won"] for player in players}

    for team in teams:
        payout = team_payouts.get(team["key"], 0.0)
        if payout and team["players"]:
            share = payout / len(team["players"])
            for player in team["players"]:
                category_amounts[(player, team_category)] += share

    def add_skin_payouts(section, category):
        if section is None:
            return
        items = simple_items(section, player_map, parse_skin_count)
        total_skins = sum(item["rank_value"] for item in items if item["rank_value"] is not None)
        pool = len(items) * OPTIONAL_GAME_BUY_IN
        if total_skins <= 0:
            return
        per_skin = pool / total_skins
        for item in items:
            if item["rank_value"] and item["rank_value"] > 0:
                category_amounts[(item["Player"], category)] += item["rank_value"] * per_skin

    add_skin_payouts(net_skins_section, "NetSkins")
    add_skin_payouts(gross_skins_section, "GrossSkins")

    for player, won_total in won_by_player.items():
        known_total = sum(amount for (name, _), amount in category_amounts.items() if name == player)
        residual = round(won_total - known_total, 2)
        if residual > 0.004:
            category_amounts[(player, "NetMedal")] += residual

    financials = []
    for (player, category), amount in sorted(category_amounts.items()):
        amount = format_amount(amount)
        if amount > 0:
            financials.append({
                "Player": player,
                "Category": category,
                "Amount": amount,
            })
    return financials


def load_canonical_date(date_str):
    result = {"scores": [], "financials": [], "handicaps": []}
    if os.path.exists(SCORES_FILE):
        scores = pd.read_csv(SCORES_FILE)
        for row in scores[scores["Date"].astype(str) == date_str].to_dict("records"):
            row.pop("Date", None)
            for col in HOLE_COLS + ["Gross_Score"]:
                if pd.notna(row.get(col)):
                    row[col] = int(float(row[col]))
            if "Differential" in row:
                row.pop("Differential", None)
            for field in ["Partner", "Team_Rank", "Individual_Rank"]:
                if pd.isna(row.get(field)):
                    row[field] = ""
            result["scores"].append(row)
    if os.path.exists(FINANCIALS_FILE):
        financials = pd.read_csv(FINANCIALS_FILE)
        for row in financials[financials["Date"].astype(str) == date_str].to_dict("records"):
            row.pop("Date", None)
            row["Amount"] = format_amount(row["Amount"])
            result["financials"].append(row)
    if os.path.exists(HANDICAPS_FILE):
        handicaps = pd.read_csv(HANDICAPS_FILE)
        for row in handicaps[handicaps["Date"].astype(str) == date_str].to_dict("records"):
            row.pop("Date", None)
            row["Handicap_Index"] = round(float(row["Handicap_Index"]), 1)
            row.pop("Course_Handicap", None)
            result["handicaps"].append(row)
    return result


def canonical_record_map(records, keys):
    mapped = {}
    for record in records:
        mapped[tuple(record.get(key, "") for key in keys)] = record
    return mapped


def reconcile_with_canonical(entry, reports):
    canonical = load_canonical_date(entry["date"])
    if not canonical["scores"] and not canonical["financials"] and not canonical["handicaps"]:
        return entry

    reconciled = dict(entry)
    for section, keys in [
        ("scores", ["Player"]),
        ("handicaps", ["Player"]),
        ("financials", ["Player", "Category"]),
    ]:
        incoming_map = canonical_record_map(reconciled.get(section, []), keys)
        canonical_map = canonical_record_map(canonical.get(section, []), keys)

        for key, canonical_record in canonical_map.items():
            incoming_record = incoming_map.get(key)
            if incoming_record is None:
                reports["canonical_added"].append({
                    "date": entry["date"],
                    "section": section,
                    "key": key,
                })
                incoming_map[key] = canonical_record
            elif json.dumps(incoming_record, sort_keys=True) != json.dumps(canonical_record, sort_keys=True):
                reports["canonical_overrides"].append({
                    "date": entry["date"],
                    "section": section,
                    "key": key,
                    "incoming": incoming_record,
                    "canonical": canonical_record,
                })
                incoming_map[key] = canonical_record

        for key in sorted(set(incoming_map) - set(canonical_map)):
            reports["incoming_not_in_canonical"].append({
                "date": entry["date"],
                "section": section,
                "key": key,
                "record": incoming_map[key],
            })

        if canonical_map:
            reconciled[section] = [canonical_map[key] for key in sorted(canonical_map)]
        else:
            reconciled[section] = [incoming_map[key] for key in sorted(incoming_map)]

    return reconciled


def infer_format_name(team_section, stableford_section):
    if team_section and team_section["title"] == "Team Quota":
        return "Team Quota"
    if stableford_section:
        return "Best Ball/Stableford"
    if team_section:
        return "Best Ball"
    return "Tournament"


def parse_squabbit_csv(path, aliases, canonical_case_map, identity_map, reconcile_canonical=False):
    reports = defaultdict(list)
    rows = read_csv_rows(path)
    meta = first_nonblank_row(rows)
    if len(meta) < 2:
        raise ValueError(f"{path}: missing tournament name/date row")

    tournament_name = meta[0].strip()
    date_str = datetime.strptime(meta[1], "%b %d, %Y").strftime("%Y-%m-%d")
    source_file = os.path.basename(path)
    players = parse_players(rows, aliases, canonical_case_map, identity_map, source_file, reports)
    seen_whs_ids = {player["WHS_ID"] for player in players if player.get("WHS_ID")}
    update_identity_seen_dates(identity_map, date_str, seen_whs_ids)
    player_map = {player["Raw_Name"]: player["Player"] for player in players}
    player_map.update({clean_player_name(player["Raw_Name"]): player["Player"] for player in players})

    round_idx = find_section(rows, "Round 1")
    if round_idx is None:
        raise ValueError(f"{path}: missing Round 1 section")

    sections = [
        section
        for section in iter_summary_sections(rows, round_idx)
        if section["title"] in {"Best Ball", "Team Quota", "Stableford", "Skins", "Strokeplay"}
    ]
    team_section = next((section for section in sections if section["title"] in {"Best Ball", "Team Quota"}), None)
    stableford_section = next((section for section in sections if section["title"] == "Stableford"), None)
    skins_sections = [section for section in sections if section["title"] == "Skins"]
    strokeplay_sections = [section for section in sections if section["title"] == "Strokeplay"]
    net_skins_section = skins_sections[0] if len(skins_sections) >= 1 else None
    gross_skins_section = skins_sections[1] if len(skins_sections) >= 2 else None
    gross_stroke_section = strokeplay_sections[-1] if strokeplay_sections else None

    teams = parse_team_section(team_section, player_map) if team_section else []
    ranked_teams = sorted([team for team in teams if team["rank_value"] is not None], key=lambda item: item["rank_value"])
    team_labels = rank_labels(ranked_teams)
    team_ranks = {}
    partners = {}
    for team in teams:
        label = team_labels.get(team["key"], "")
        if team["rank_value"] is None:
            reports["incomplete_team_rows"].append({
                "date": date_str,
                "team": team["label"],
                "players": team["players"],
            })
        for player in team["players"]:
            others = [other for other in team["players"] if other != player]
            partners[player] = others[0] if others else ""
            team_ranks[player] = label

    individual_ranks = {}
    if gross_stroke_section:
        gross_items = sorted(simple_items(gross_stroke_section, player_map), key=lambda item: item["rank_value"])
        individual_ranks = rank_labels(gross_items)

    scores, labels_by_player = parse_scorecards(rows, player_map, partners, team_ranks, individual_ranks)
    scored_players = {score["Player"] for score in scores}
    player_lookup = {player["Player"]: player for player in players}
    handicaps = []
    for player in sorted(scored_players):
        player_info = player_lookup.get(player)
        if not player_info:
            reports["players_missing_from_players_section"].append({"date": date_str, "player": player})
            continue
        if player_info["Handicap_Index"] is None:
            reports["missing_handicaps"].append({"date": date_str, "player": player})
            continue
        handicaps.append({
            "Player": player,
            "Handicap_Index": round(float(player_info["Handicap_Index"]), 1),
        })

    team_category = "Quota" if team_section and team_section["title"] == "Team Quota" else "BestBall"
    team_pool = sum(len(team["players"]) for team in teams) * TEAM_BUY_IN
    team_payouts = payout_by_rank(ranked_teams, team_pool)
    financials = build_financials(
        players,
        team_category,
        teams,
        team_payouts,
        net_skins_section,
        gross_skins_section,
        player_map,
    )

    won_by_player = {player["Player"]: player["Won"] for player in players}
    financial_totals = defaultdict(float)
    for row in financials:
        financial_totals[row["Player"]] += row["Amount"]
    for player, won_total in sorted(won_by_player.items()):
        if abs(round(financial_totals[player], 2) - round(won_total, 2)) > 0.02:
            reports["won_reconciliation_issues"].append({
                "date": date_str,
                "player": player,
                "squabbit_won": round(won_total, 2),
                "derived_won": round(financial_totals[player], 2),
            })

    entry = {
        "date": date_str,
        "metadata": {
            "full_scorecard_available": True,
            "handicap_list_available": True,
            "source": "squabbit_csv",
            "source_file": source_file,
            "tournament_name": tournament_name,
            "format_name": infer_format_name(team_section, stableford_section),
            "screenshots": [],
            "source_notes": [
                "Generated from Squabbit CSV export.",
                "Player display names were normalized before canonical ingest.",
                "Financial category rows were derived from Squabbit standings, buy-ins, skins counts, and player total winnings.",
            ],
            "approximations": [],
        },
        "scores": sorted(scores, key=lambda row: row["Player"]),
        "financials": sorted(financials, key=lambda row: (row["Player"], row["Category"])),
        "handicaps": sorted(handicaps, key=lambda row: row["Player"]),
    }

    if reconcile_canonical:
        entry = reconcile_with_canonical(entry, reports)

    reports["summary"].append({
        "date": date_str,
        "source_file": source_file,
        "tournament_name": tournament_name,
        "players": len(players),
        "scores": len(entry["scores"]),
        "financials": len(entry["financials"]),
        "handicaps": len(entry["handicaps"]),
        "team_category": team_category,
        "team_pool": format_amount(team_pool),
        "game_labels": {player: labels for player, labels in sorted(labels_by_player.items())},
    })
    return entry, reports


def merge_reports(target, source):
    for key, values in source.items():
        target[key].extend(values)


def write_tournaments_file(path, entries):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fieldnames = ["Tournament_ID", "Date", "Season", "Name", "Format", "Source_File", "Status"]
    rows_by_date = {}
    if os.path.exists(path):
        with open(path, newline="") as input_file:
            for row in csv.DictReader(input_file):
                if row.get("Date"):
                    rows_by_date[row["Date"]] = {field: row.get(field, "") for field in fieldnames}

    for entry in entries:
        date = datetime.strptime(entry["date"], "%Y-%m-%d")
        season = date.year + 1 if date.month >= 11 else date.year
        rows_by_date[entry["date"]] = {
            "Tournament_ID": f"{season}-{date:%m%d}",
            "Date": entry["date"],
            "Season": season,
            "Name": entry["metadata"].get("tournament_name", "") or entry["metadata"].get("source_file", ""),
            "Format": entry["metadata"].get("format_name", ""),
            "Source_File": entry["metadata"].get("source_file", ""),
            "Status": "completed",
        }
    with open(path, "w", newline="") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=fieldnames)
        writer.writeheader()
        for row in sorted(rows_by_date.values(), key=lambda item: item["Date"]):
            writer.writerow(row)


def print_report(reports):
    print("Squabbit CSV import report")
    for summary in reports.get("summary", []):
        print(
            "  {date}: {scores} scores, {handicaps} handicaps, {financials} financial rows from {source_file}".format(
                **summary
            )
        )
    for key in [
        "name_rewrites",
        "identity_conflicts",
        "incomplete_team_rows",
        "missing_handicaps",
        "won_reconciliation_issues",
        "canonical_added",
        "canonical_overrides",
        "incoming_not_in_canonical",
    ]:
        values = reports.get(key, [])
        print(f"  {key}: {len(values)}")
        for item in values[:20]:
            if key == "canonical_overrides":
                print(f"    - {item['date']} | {item['section']} | {item['key']}")
            elif key == "incoming_not_in_canonical":
                print(f"    - {item['date']} | {item['section']} | {item['key']} (dropped because canonical exists)")
            else:
                print(f"    - {item}")
        if len(values) > 20:
            print(f"    - ... and {len(values) - 20} more")


def plain_report_value(value):
    if isinstance(value, defaultdict):
        return {key: plain_report_value(item) for key, item in value.items()}
    if isinstance(value, dict):
        return {key: plain_report_value(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [plain_report_value(item) for item in value]
    if isinstance(value, list):
        return [plain_report_value(item) for item in value]
    return value


def report_item_summary(key, item):
    if key == "canonical_overrides":
        return "{date} | {section} | {item_key}".format(
            date=item["date"],
            section=item["section"],
            item_key=item["key"],
        )
    if key == "incoming_not_in_canonical":
        return "{date} | {section} | {item_key} (dropped because canonical exists)".format(
            date=item["date"],
            section=item["section"],
            item_key=item["key"],
        )
    return str(item)


def write_reconciliation_reports(json_path, md_path, reports):
    plain_reports = plain_report_value(dict(reports))

    if json_path:
        json_dir = os.path.dirname(json_path)
        if json_dir:
            os.makedirs(json_dir, exist_ok=True)
        with open(json_path, "w") as output_file:
            json.dump(plain_reports, output_file, indent=2)
            output_file.write("\n")

    if not md_path:
        return

    md_dir = os.path.dirname(md_path)
    if md_dir:
        os.makedirs(md_dir, exist_ok=True)
    review_keys = [
        "name_rewrites",
        "identity_conflicts",
        "incomplete_team_rows",
        "missing_handicaps",
        "players_missing_from_players_section",
        "won_reconciliation_issues",
        "canonical_added",
        "canonical_overrides",
        "incoming_not_in_canonical",
    ]

    lines = [
        "# Squabbit Reconciliation Report",
        "",
        "Generated by `scripts/import_squabbit_csv.py`.",
        "",
        "## Summary",
        "",
    ]
    for summary in reports.get("summary", []):
        lines.append(
            "- {date}: {scores} scores, {handicaps} handicaps, {financials} financial rows from `{source_file}`".format(
                **summary
            )
        )

    lines.extend([
        "",
        "## Review Counts",
        "",
    ])
    for key in review_keys:
        lines.append(f"- `{key}`: {len(reports.get(key, []))}")

    lines.extend([
        "",
        "## Review Details",
        "",
        "Canonical rows are authoritative for dates already present in `data/`. Incoming Squabbit-only rows for those dates are reported here and dropped from the generated reviewed JSON.",
        "",
    ])
    for key in review_keys:
        values = reports.get(key, [])
        if not values:
            continue
        lines.append(f"### {key}")
        lines.append("")
        for item in values[:50]:
            lines.append(f"- {report_item_summary(key, item)}")
        if len(values) > 50:
            lines.append(f"- ... and {len(values) - 50} more")
        lines.append("")

    with open(md_path, "w") as output_file:
        output_file.write("\n".join(lines).rstrip() + "\n")


def main():
    parser = argparse.ArgumentParser(description="Import Squabbit tournament CSV exports into reviewed JSON.")
    parser.add_argument("csv_files", nargs="+", help="One or more Squabbit CSV export files")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="Output JSON path")
    parser.add_argument("--report-output", default=DEFAULT_REPORT_JSON, help="Output reconciliation report JSON path")
    parser.add_argument("--report-md-output", default=DEFAULT_REPORT_MD, help="Output reconciliation report Markdown path")
    parser.add_argument("--identity-map", default=DEFAULT_IDENTITY_MAP, help="Local WHS/Squabbit identity map path")
    parser.add_argument("--no-reconcile-canonical", action="store_true", help="Do not prefer existing canonical rows for matching dates")
    parser.add_argument("--tournaments-out", help="Optional tournaments.csv output path")
    parser.add_argument("--dry-run", action="store_true", help="Parse and report without writing files")
    args = parser.parse_args()

    aliases = load_aliases()
    canonical_case_map = load_canonical_names()
    identity_map = load_identity_map(args.identity_map)
    all_reports = defaultdict(list)
    entries = []

    for csv_file in args.csv_files:
        entry, reports = parse_squabbit_csv(
            csv_file,
            aliases,
            canonical_case_map,
            identity_map,
            reconcile_canonical=not args.no_reconcile_canonical,
        )
        entries.append(entry)
        merge_reports(all_reports, reports)

    payload = {"update_batch": sorted(entries, key=lambda entry: entry["date"])} if len(entries) > 1 else entries[0]
    print_report(all_reports)

    if args.dry_run:
        print("Dry run complete. No files written.")
        return

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w") as output_file:
        json.dump(payload, output_file, indent=2)
        output_file.write("\n")
    write_identity_map(args.identity_map, identity_map)
    write_reconciliation_reports(args.report_output, args.report_md_output, all_reports)
    if args.tournaments_out:
        write_tournaments_file(args.tournaments_out, entries)
    print(f"Wrote {args.output}")
    print(f"Wrote {args.identity_map}")
    if args.report_output:
        print(f"Wrote {args.report_output}")
    if args.report_md_output:
        print(f"Wrote {args.report_md_output}")
    if args.tournaments_out:
        print(f"Wrote {args.tournaments_out}")


if __name__ == "__main__":
    main()
