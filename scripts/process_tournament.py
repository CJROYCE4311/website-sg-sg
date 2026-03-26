#!/usr/bin/env python3
"""
Single entry point for processing tournament data.

Usage:
    python scripts/process_tournament.py input/tournament_data.json
    python scripts/process_tournament.py input/tournament_data.json --commit
    python scripts/process_tournament.py input/tournament_data.json --commit --push

This script:
1. Validates the JSON data
2. Ingests data into CSVs
3. Archives the JSON to input/history/
4. Moves screenshots to input/processed/YYYY-MM-DD/
5. Regenerates the website
6. Optionally commits and pushes to git
"""

import os
import sys
import json
import shutil
import argparse
import subprocess
from glob import glob

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
SCREENSHOTS_DIR = os.path.join(PROJECT_ROOT, "input", "screenshots")
PROCESSED_DIR = os.path.join(PROJECT_ROOT, "input", "processed")
PUBLISH_PATHS = ["data", "website"]


def get_tournament_label(json_file):
    """Extract a stable label from the JSON file for display and archiving."""
    with open(json_file, 'r') as f:
        data = json.load(f)

    if 'update_batch' in data:
        dates = sorted({entry.get('date') for entry in data['update_batch'] if entry.get('date')})
        if not dates:
            return None
        if len(dates) == 1:
            return dates[0]
        return f"{dates[0]}_to_{dates[-1]}"
    return data.get('date')


def archive_screenshots(date_str):
    """Move screenshots to processed folder."""
    if not date_str:
        print("⚠️  No date provided, skipping screenshot archiving")
        return

    # Find screenshots
    screenshots = []
    for ext in ['*.png', '*.jpg', '*.jpeg', '*.PNG', '*.JPG', '*.JPEG']:
        screenshots.extend(glob(os.path.join(SCREENSHOTS_DIR, ext)))

    if not screenshots:
        print("📷 No screenshots found to archive")
        return

    # Create destination folder
    dest_dir = os.path.join(PROCESSED_DIR, date_str)
    os.makedirs(dest_dir, exist_ok=True)

    # Move screenshots
    for screenshot in screenshots:
        filename = os.path.basename(screenshot)
        dest_path = os.path.join(dest_dir, filename)

        # Handle duplicates
        counter = 1
        base, ext = os.path.splitext(filename)
        while os.path.exists(dest_path):
            dest_path = os.path.join(dest_dir, f"{base}_{counter}{ext}")
            counter += 1

        shutil.move(screenshot, dest_path)

    print(f"📷 Archived {len(screenshots)} screenshot(s) to input/processed/{date_str}/")


def get_repo_changes():
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    changes = []
    for line in result.stdout.splitlines():
        if not line:
            continue
        status = line[:2]
        path = line[3:]
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        changes.append((status, path))
    return changes


def enforce_publish_scope():
    changes = get_repo_changes()
    unexpected = [
        path for _, path in changes
        if not any(path == allowed or path.startswith(f"{allowed}/") for allowed in PUBLISH_PATHS)
    ]
    if unexpected:
        print("❌ Refusing to publish with unrelated repo changes present:")
        for path in unexpected:
            print(f"   - {path}")
        print("\nClean, ignore, or commit those files separately and retry publish.")
        return False
    return True


def stage_publish_paths():
    subprocess.run(["git", "add", "--", *PUBLISH_PATHS], cwd=PROJECT_ROOT, check=True)


def git_commit(date_str, push=False):
    """Commit changes to git."""
    print("\n📝 Committing changes...")

    if not enforce_publish_scope():
        return False

    stage_publish_paths()

    # Create commit message
    msg = f"Add tournament results for {date_str}"

    result = subprocess.run(
        ["git", "commit", "-m", msg],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        print(f"   ✅ Committed: {msg}")
    elif "nothing to commit" in result.stdout + result.stderr:
        print("   ℹ️  Nothing to commit")
        return True
    else:
        print(f"   ❌ Commit failed: {result.stderr}")
        return False

    if push:
        print("🚀 Pushing to remote...")
        result = subprocess.run(
            ["git", "push"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print("   ✅ Pushed to remote")
        else:
            print(f"   ❌ Push failed: {result.stderr}")
            return False
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Process tournament data end-to-end.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Process data only:
    python scripts/process_tournament.py input/tournament_data.json

  Validate only:
    python scripts/process_tournament.py input/tournament_data.json --dry-run

  Process and commit:
    python scripts/process_tournament.py input/tournament_data.json --commit

  Process, commit, and push:
    python scripts/process_tournament.py input/tournament_data.json --commit --push

  Skip screenshot archiving:
    python scripts/process_tournament.py input/tournament_data.json --no-archive-screenshots
        """
    )
    parser.add_argument("json_file", help="Path to tournament JSON file")
    parser.add_argument("--commit", action="store_true", help="Commit changes to git")
    parser.add_argument("--push", action="store_true", help="Push to remote (implies --commit)")
    parser.add_argument("--no-archive-screenshots", action="store_true",
                        help="Don't move screenshots to processed folder")
    parser.add_argument("--skip-validation", action="store_true",
                        help="Skip data validation (not recommended)")
    parser.add_argument("--skip-site-update", action="store_true",
                        help="Don't regenerate website files after ingestion")
    parser.add_argument("--dry-run", action="store_true",
                        help="Validate and simulate processing without writing files")
    parser.add_argument("--allow-incomplete", action="store_true",
                        help="Allow incomplete score/handicap coverage to pass through ingest")

    args = parser.parse_args()

    # Validate JSON file exists
    if not os.path.exists(args.json_file):
        print(f"❌ File not found: {args.json_file}")
        sys.exit(1)

    print("=" * 50)
    print("🏌️  SG@SG Tournament Processor")
    print("=" * 50)

    # Get tournament date
    date_str = get_tournament_label(args.json_file)
    if date_str:
        print(f"📅 Tournament Label: {date_str}")
    else:
        print("⚠️  Warning: No date found in JSON")

    # Run ingestion (includes validation, archiving JSON, and site update)
    print("\n" + "-" * 50)
    venv_python = os.path.join(PROJECT_ROOT, "venv", "bin", "python")
    if not os.path.exists(venv_python):
        venv_python = sys.executable

    ingest_args = [venv_python, os.path.join(SCRIPT_DIR, "ingest_data.py"), args.json_file]
    if args.skip_validation:
        ingest_args.append("--skip-validation")
    if args.skip_site_update:
        ingest_args.append("--skip-site-update")
    if args.dry_run:
        ingest_args.append("--dry-run")
    if args.allow_incomplete:
        ingest_args.append("--allow-incomplete")

    result = subprocess.run(ingest_args, cwd=PROJECT_ROOT)

    if result.returncode != 0:
        print("\n❌ Ingestion failed. Aborting.")
        sys.exit(1)

    # Archive screenshots
    if not args.dry_run and not args.no_archive_screenshots and date_str:
        print("\n" + "-" * 50)
        archive_screenshots(date_str)

    # Git operations
    if args.dry_run and (args.commit or args.push):
        print("\n⚠️  Dry run requested. Skipping git operations.")
    elif args.commit or args.push:
        print("\n" + "-" * 50)
        if not git_commit(date_str, push=args.push):
            sys.exit(1)

    print("\n" + "=" * 50)
    print("✅ Tournament processing complete!")
    print("=" * 50)


if __name__ == "__main__":
    main()
