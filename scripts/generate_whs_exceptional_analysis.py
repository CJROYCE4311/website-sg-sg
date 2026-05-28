import json
import math
import os
from datetime import date, datetime

import pandas as pd


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
WEBSITE_DATA_DIR = os.path.join(PROJECT_ROOT, "website", "data")

SCORES_FILE = os.path.join(DATA_DIR, "scores.csv")
HANDICAPS_FILE = os.path.join(DATA_DIR, "handicaps.csv")
TOURNAMENTS_FILE = os.path.join(DATA_DIR, "tournaments.csv")

SEASON = 2026
SEASON_START = date(2025, 11, 1)
COURSE_RATING = 70.5
SLOPE_RATING = 124
COURSE_PAR = 72
BASE_SLOPE = 113
EXCEPTIONAL_THRESHOLD = 7.0


PROBABILITY_TABLE = {
    (None, 5.9): {
        (0.0, 0.9): 5,
        (1.0, 1.9): 10,
        (2.0, 2.9): 23,
        (3.0, 3.9): 57,
        (4.0, 4.9): 151,
        (5.0, 5.9): 379,
        (6.0, 6.9): 790,
        (7.0, 7.9): 2349,
        (8.0, 8.9): 20111,
        (9.0, 9.9): 48219,
        (10.0, None): 125000,
    },
    (6.0, 12.9): {
        (0.0, 0.9): 5,
        (1.0, 1.9): 10,
        (2.0, 2.9): 22,
        (3.0, 3.9): 51,
        (4.0, 4.9): 121,
        (5.0, 5.9): 276,
        (6.0, 6.9): 536,
        (7.0, 7.9): 1200,
        (8.0, 8.9): 4467,
        (9.0, 9.9): 27877,
        (10.0, None): 84300,
    },
    (13.0, 21.9): {
        (0.0, 0.9): 5,
        (1.0, 1.9): 10,
        (2.0, 2.9): 21,
        (3.0, 3.9): 43,
        (4.0, 4.9): 87,
        (5.0, 5.9): 174,
        (6.0, 6.9): 323,
        (7.0, 7.9): 552,
        (8.0, 8.9): 1138,
        (9.0, 9.9): 3577,
        (10.0, None): 37000,
    },
    (22.0, 30.9): {
        (0.0, 0.9): 5,
        (1.0, 1.9): 8,
        (2.0, 2.9): 13,
        (3.0, 3.9): 23,
        (4.0, 4.9): 40,
        (5.0, 5.9): 72,
        (6.0, 6.9): 130,
        (7.0, 7.9): 229,
        (8.0, 8.9): 382,
        (9.0, 9.9): 695,
        (10.0, None): 1650,
    },
    (31.0, None): {
        (0.0, 0.9): 5,
        (1.0, 1.9): 7,
        (2.0, 2.9): 10,
        (3.0, 3.9): 15,
        (4.0, 4.9): 22,
        (5.0, 5.9): 35,
        (6.0, 6.9): 60,
        (7.0, 7.9): 101,
        (8.0, 8.9): 185,
        (9.0, 9.9): 359,
        (10.0, None): 874,
    },
}


def tournament_year(value):
    value = pd.to_datetime(value)
    return value.year + 1 if value.month >= 11 else value.year


def to_number(value):
    if value is None or pd.isna(value):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number):
        return None
    return number


def round_or_none(value, digits=1):
    number = to_number(value)
    return None if number is None else round(number, digits)


def calculate_course_handicap(index_value):
    index_number = to_number(index_value)
    if index_number is None:
        return None
    return round(index_number * SLOPE_RATING / BASE_SLOPE + (COURSE_RATING - COURSE_PAR), 1)


def target_differential(gross_score):
    gross_number = to_number(gross_score)
    if gross_number is None:
        return None
    return round((BASE_SLOPE / SLOPE_RATING) * (gross_number - COURSE_RATING), 1)


def probability_for(index, strokes_better):
    index_number = to_number(index)
    strokes_number = to_number(strokes_better)
    if index_number is None or strokes_number is None:
        return {
            "frequency": None,
            "percent": None,
            "display": "Missing handicap index",
            "handicap_band": None,
            "strokes_band": None,
        }

    lookup_strokes = max(0.0, strokes_number)
    handicap_band = None
    table = None
    for band, rows in PROBABILITY_TABLE.items():
        low, high = band
        if (low is None or index_number >= low) and (high is None or index_number <= high):
            handicap_band = display_band(low, high)
            table = rows
            break

    if table is None:
        return {
            "frequency": None,
            "percent": None,
            "display": "Outside Appendix E table",
            "handicap_band": None,
            "strokes_band": None,
        }

    for band, frequency in table.items():
        low, high = band
        if lookup_strokes >= low and (high is None or lookup_strokes <= high):
            percent = round(100.0 / frequency, 4)
            return {
                "frequency": frequency,
                "percent": percent,
                "display": probability_display(frequency),
                "handicap_band": handicap_band,
                "strokes_band": display_band(low, high),
            }

    return {
        "frequency": None,
        "percent": None,
        "display": "Outside Appendix E table",
        "handicap_band": handicap_band,
        "strokes_band": None,
    }


def display_band(low, high):
    if low is None:
        return f"<= {high:.1f}"
    if high is None:
        return f"{low:.1f}+"
    return f"{low:.1f}-{high:.1f}"


def probability_display(frequency):
    percent = 100.0 / frequency
    if percent >= 10:
        percent_text = f"{percent:.1f}%"
    elif percent >= 1:
        percent_text = trim_percent(percent, 3)
    else:
        percent_text = trim_percent(percent, 4)
    return f"{percent_text} or 1 in {frequency:,} rounds"


def trim_percent(value, digits):
    return f"{value:.{digits}f}".rstrip("0").rstrip(".") + "%"


def performance_text(strokes_better):
    number = to_number(strokes_better)
    if number is None:
        return "Missing handicap index"
    if number >= EXCEPTIONAL_THRESHOLD:
        return "Exceptional"
    if number >= 5.0:
        return "Elite"
    if number >= 3.0:
        return "Great"
    if number >= 0.0:
        return "At or better than index"
    return "Worse than index"


def merge_sources():
    scores = pd.read_csv(SCORES_FILE, parse_dates=["Date"])
    handicaps = pd.read_csv(HANDICAPS_FILE, parse_dates=["Date"]) if os.path.exists(HANDICAPS_FILE) else pd.DataFrame()
    tournaments = pd.read_csv(TOURNAMENTS_FILE, parse_dates=["Date"]) if os.path.exists(TOURNAMENTS_FILE) else pd.DataFrame()

    if tournaments.empty:
        scores["Season"] = scores["Date"].apply(tournament_year)
        tournament_rows = (
            scores[scores["Season"] == SEASON][["Date"]]
            .drop_duplicates()
            .assign(
                Tournament_ID=lambda frame: frame["Date"].dt.strftime("%Y-%m-%d"),
                Name=lambda frame: "SG@SG " + frame["Date"].dt.strftime("%b %-d"),
                Format="Tournament",
                Status="completed",
            )
        )
    else:
        tournaments["Season"] = pd.to_numeric(tournaments["Season"], errors="coerce")
        tournament_rows = tournaments[
            (tournaments["Season"] == SEASON)
            & (tournaments["Date"].dt.date >= SEASON_START)
            & (tournaments["Date"].dt.date <= date.today())
            & (tournaments["Status"].astype(str).str.lower() == "completed")
        ].copy()

    if handicaps.empty:
        handicaps = pd.DataFrame(columns=["Date", "Player", "Handicap_Index", "Course_Handicap"])
    else:
        handicaps["Handicap_Index"] = pd.to_numeric(handicaps.get("Handicap_Index"), errors="coerce")
        if "Course_Handicap" not in handicaps.columns:
            handicaps["Course_Handicap"] = pd.NA
        handicaps["Course_Handicap"] = pd.to_numeric(handicaps["Course_Handicap"], errors="coerce")
        missing_course = handicaps["Course_Handicap"].isna() & handicaps["Handicap_Index"].notna()
        handicaps.loc[missing_course, "Course_Handicap"] = handicaps.loc[missing_course, "Handicap_Index"].apply(
            calculate_course_handicap
        )
        handicaps = handicaps.drop_duplicates(subset=["Date", "Player"], keep="last")

    scores["Gross_Score"] = pd.to_numeric(scores["Gross_Score"], errors="coerce")
    season_scores = scores.merge(
        tournament_rows[["Tournament_ID", "Date", "Name", "Format"]],
        on="Date",
        how="inner",
    )
    season_scores = season_scores.merge(
        handicaps[["Date", "Player", "Handicap_Index", "Course_Handicap"]],
        on=["Date", "Player"],
        how="left",
    )
    return tournament_rows.sort_values("Date", ascending=False), season_scores


def build_player_rows(rows):
    player_rows = []
    for _, row in rows.iterrows():
        gross = round_or_none(row.get("Gross_Score"), 0)
        course_hcp = round_or_none(row.get("Course_Handicap"), 1)
        index = round_or_none(row.get("Handicap_Index"), 1)
        differential = target_differential(gross)
        net_score = None if gross is None or course_hcp is None else round(gross - course_hcp, 1)
        net_to_par = None if net_score is None else round(net_score - COURSE_PAR, 1)
        strokes_better = None if index is None or differential is None else round(index - differential, 1)
        probability = probability_for(index, strokes_better)
        current_gap = None if differential is None or course_hcp is None else round(differential - course_hcp, 1)
        notes = []
        if index is None:
            notes.append("Missing handicap index")
        if course_hcp is None:
            notes.append("Missing course handicap")
        if gross is None:
            notes.append("Missing gross score")

        player_rows.append(
            {
                "net_rank": None,
                "player": str(row.get("Player") or ""),
                "gross_score": gross,
                "course_handicap": course_hcp,
                "net_score": net_score,
                "net_to_par": net_to_par,
                "handicap_index": index,
                "target_differential": differential,
                "strokes_better_than_index": strokes_better,
                "probability": probability,
                "current_model_gap": current_gap,
                "classification": performance_text(strokes_better),
                "exceptional": bool(strokes_better is not None and strokes_better >= EXCEPTIONAL_THRESHOLD),
                "notes": "; ".join(notes),
            }
        )

    player_rows.sort(
        key=lambda item: (
            item["net_score"] is None,
            item["net_score"] if item["net_score"] is not None else 999,
            item["gross_score"] if item["gross_score"] is not None else 999,
            item["player"].lower(),
        )
    )
    assign_net_ranks(player_rows)
    return player_rows


def assign_net_ranks(rows):
    last_score = object()
    current_rank = 0
    for index, row in enumerate(rows, start=1):
        net_score = row.get("net_score")
        if net_score is None:
            row["net_rank"] = None
            continue
        if net_score != last_score:
            current_rank = index
            last_score = net_score
        row["net_rank"] = current_rank


def build_export():
    tournaments, season_scores = merge_sources()
    tournament_exports = []

    for _, tournament in tournaments.iterrows():
        date_value = pd.to_datetime(tournament["Date"])
        date_str = date_value.strftime("%Y-%m-%d")
        rows = season_scores[season_scores["Date"] == date_value].copy()
        player_rows = build_player_rows(rows)
        net_values = [row["net_score"] for row in player_rows if row["net_score"] is not None]
        tournament_exports.append(
            {
                "tournament_id": str(tournament.get("Tournament_ID") or date_str),
                "date": date_str,
                "name": str(tournament.get("Name") or f"SG@SG {date_str}"),
                "format": str(tournament.get("Format") or "Tournament"),
                "players": len(player_rows),
                "with_handicap": sum(1 for row in player_rows if row["handicap_index"] is not None),
                "exceptional_rounds": sum(1 for row in player_rows if row["exceptional"]),
                "lowest_net": min(net_values) if net_values else None,
                "highest_net": max(net_values) if net_values else None,
                "rows": player_rows,
            }
        )

    all_rows = [row for tournament in tournament_exports for row in tournament["rows"]]
    export = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "season": SEASON,
        "season_start": SEASON_START.isoformat(),
        "course": {
            "name": "Sterling Grove Golf and Country Club",
            "par": COURSE_PAR,
            "course_rating": COURSE_RATING,
            "slope": SLOPE_RATING,
        },
        "methodology": {
            "target_differential_formula": "(113 / slope) * (gross_score - course_rating)",
            "strokes_better_formula": "handicap_index - target_differential",
            "exceptional_threshold": EXCEPTIONAL_THRESHOLD,
            "probability_source": "USGA Appendix E Exceptional Tournament Score Probability Table",
            "sort_order": "Tournament date descending; player net score ascending within each tournament.",
        },
        "summary": {
            "tournaments": len(tournament_exports),
            "player_rounds": len(all_rows),
            "with_handicap": sum(1 for row in all_rows if row["handicap_index"] is not None),
            "exceptional_rounds": sum(1 for row in all_rows if row["exceptional"]),
        },
        "tournaments": tournament_exports,
    }
    return export


def write_export(export):
    os.makedirs(WEBSITE_DATA_DIR, exist_ok=True)
    json_path = os.path.join(WEBSITE_DATA_DIR, "whs_exceptional_analysis.json")
    js_path = os.path.join(WEBSITE_DATA_DIR, "whs_exceptional_analysis.js")

    with open(json_path, "w") as output:
        json.dump(export, output, indent=2)
        output.write("\n")

    js_content = f"const whsExceptionalAnalysis = {json.dumps(export, indent=2)};\n"
    with open(js_path, "w") as output:
        output.write(js_content)

    print(f"Generated {json_path}")
    print(f"Generated {js_path}")


def main():
    export = build_export()
    write_export(export)
    summary = export["summary"]
    print(
        "WHS exceptional analysis: "
        f"{summary['tournaments']} tournaments, "
        f"{summary['player_rounds']} player-rounds, "
        f"{summary['exceptional_rounds']} exceptional flags."
    )


if __name__ == "__main__":
    main()
