#!/usr/bin/env python3
import argparse
import json
import os
import sys

from ingest_data import (
    build_canonical_audit,
    load_db,
    load_player_aliases,
    normalize_payload_names,
    print_canonical_audit,
    validate_data,
)


def audit_payload(json_file):
    with open(json_file, 'r') as f:
        data = json.load(f)

    aliases = load_player_aliases()
    normalized, rewrites = normalize_payload_names(data, aliases)

    print("🧾 Reviewed Payload Audit")
    if rewrites:
        print(f"   - Alias rewrites: {len(rewrites)}")
        for rewrite in rewrites:
            print(
                "     * {section}.{field}: {from_name} -> {to_name}".format(
                    section=rewrite['section'],
                    field=rewrite['field'],
                    from_name=rewrite['from'],
                    to_name=rewrite['to'],
                )
            )
    else:
        print("   - Alias rewrites: 0")

    entries = normalized.get('update_batch', [normalized])
    for entry in entries:
        is_valid, errors, warnings = validate_data(entry)
        print(f"   - {entry.get('date', 'unknown')}: {len(errors)} errors, {len(warnings)} warnings")
        metadata = entry.get('metadata') or {}
        approximations = metadata.get('approximations', []) or []
        if approximations:
            print(f"     * approximations: {len(approximations)}")
        if not is_valid:
            for error in errors:
                print(f"     * error: {error}")


def main():
    parser = argparse.ArgumentParser(description="Audit canonical CSVs and optionally a reviewed JSON payload.")
    parser.add_argument("--json-file", help="Optional reviewed tournament JSON to audit before ingest")
    args = parser.parse_args()

    scores, financials, handicaps = load_db()
    audit = build_canonical_audit(scores, financials, handicaps)
    print_canonical_audit(audit)

    if args.json_file:
        if not os.path.exists(args.json_file):
            print(f"\n❌ JSON file not found: {args.json_file}")
            sys.exit(1)
        print()
        audit_payload(args.json_file)

    fatal = bool(audit['duplicate_issues']) or not audit['missing_snapshots'].empty
    sys.exit(1 if fatal else 0)


if __name__ == "__main__":
    main()
