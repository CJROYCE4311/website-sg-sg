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
from datetime import datetime
from glob import glob

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
SCREENSHOTS_DIR = os.path.join(PROJECT_ROOT, "input", "screenshots")
PROCESSED_DIR = os.path.join(PROJECT_ROOT, "input", "processed")


def get_tournament_date(json_file):
    """Extract the tournament date from JSON file."""
    with open(json_file, 'r') as f:
        data = json.load(f)

    if 'update_batch' in data:
        # Use the first date in batch
        return data['update_batch'][0].get('date')
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


def git_commit(date_str, push=False):
    """Commit changes to git."""
    print("\n📝 Committing changes...")

    # Stage all changes
    subprocess.run(["git", "add", "."], cwd=PROJECT_ROOT, check=True)

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
        return
    else:
        print(f"   ❌ Commit failed: {result.stderr}")
        return

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


def main():
    parser = argparse.ArgumentParser(
        description="Process tournament data end-to-end.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Process data only:
    python scripts/process_tournament.py input/tournament_data.json

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

    args = parser.parse_args()

    # Validate JSON file exists
    if not os.path.exists(args.json_file):
        print(f"❌ File not found: {args.json_file}")
        sys.exit(1)

    print("=" * 50)
    print("🏌️  SG@SG Tournament Processor")
    print("=" * 50)

    # Get tournament date
    date_str = get_tournament_date(args.json_file)
    if date_str:
        print(f"📅 Tournament Date: {date_str}")
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

    result = subprocess.run(ingest_args, cwd=PROJECT_ROOT)

    if result.returncode != 0:
        print("\n❌ Ingestion failed. Aborting.")
        sys.exit(1)

    # Archive screenshots
    if not args.no_archive_screenshots and date_str:
        print("\n" + "-" * 50)
        archive_screenshots(date_str)

    # Git operations
    if args.commit or args.push:
        print("\n" + "-" * 50)
        git_commit(date_str, push=args.push)

    print("\n" + "=" * 50)
    print("✅ Tournament processing complete!")
    print("=" * 50)


if __name__ == "__main__":
    main()
