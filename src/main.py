#!/usr/bin/env python3
"""
Music Organizer – CLI for organizing music libraries by genre.

Usage examples:
  python -m music_organizer.scanner <src> <dest> --mode copy --level general
  python -m music_organizer.scanner <src> <dest> --mode move --level both --dry-run
"""

import argparse
import os
import sys
from typing import Dict, List

# Add parent directory to path for running as module
# (Not strictly needed for python -m, but kept for direct execution)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .scanner import scan_source_directory, is_inside_dest
from .classify import classify_file
from .fileops import compute_destination, copy_file, move_file, ensure_dir_exists
from .reporting import write_csv_report, print_summary


def parse_args():
    parser = argparse.ArgumentParser(
        description="Organize music files by genre using metadata, path, and filename analysis."
    )
    parser.add_argument(
        "source",
        help="Root folder of the music library to organize (will be scanned recursively).",
    )
    parser.add_argument(
        "destination",
        help="Destination root folder where organized genre folders will be created.",
    )
    parser.add_argument(
        "--mode",
        choices=["copy", "move"],
        default="copy",
        help="File operation mode: copy (default, preserves originals) or move.",
    )
    parser.add_argument(
        "--level",
        choices=["general", "specific", "both"],
        default="general",
        help="Genre classification level: general (broad buckets), specific (detailed subgenres), or both (nests specific under general).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would happen without actually copying/moving files.",
    )
    parser.add_argument(
        "--report",
        metavar="CSV_PATH",
        help="Optional: write a CSV report with details of each processed file.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit the number of files to process (useful for testing).",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug output (shows metadata reads, classification decisions).",
    )
    parser.add_argument(
        "--skip-unknown-only",
        action="store_true",
        help="Process only files that would end up in 'Unknown'. Useful for targeted re-classification attempts.",
    )
    return parser.parse_args()


def should_process_file(
    src_file: str,
    dest_dir: str,
    skip_unknown_only: bool,
    classification: Tuple[str, str, str],
) -> bool:
    """
    Determine whether a file should be processed based on flags like --skip-unknown-only.
    """
    if not skip_unknown_only:
        return True

    specific, general, reason = classification
    return specific == "Unknown" or general == "Other / Unknown"


def main():
    args = parse_args()

    src_dir = os.path.abspath(args.source)
    dest_dir = os.path.abspath(args.destination)

    if not os.path.isdir(src_dir):
        print(f"Error: Source directory does not exist: {src_dir}")
        sys.exit(1)

    # Ensure destination exists (even in dry-run for reporting)
    if not args.dry_run:
        ensure_dir_exists(dest_dir)

    if args.debug:
        print(f"[DEBUG] Source: {src_dir}")
        print(f"[DEBUG] Destination: {dest_dir}")
        print(f"[DEBUG] Mode: {args.mode}")
        print(f"[DEBUG] Level: {args.level}")
        print(f"[DEBUG] Dry run: {args.dry_run}")
        if args.limit:
            print(f"[DEBUG] Limit: {args.limit}")
        print("[DEBUG] Scanning files...")

    # Scan for files
    try:
        files = scan_source_directory(src_dir, limit=args.limit, debug=args.debug)
    except Exception as e:
        print(f"Error scanning source directory: {e}")
        sys.exit(1)

    total_files = len(files)
    if total_files == 0:
        print("No audio files found in source directory.")
        sys.exit(0)

    print(f"Found {total_files} audio file(s). Starting organization...")

    # Statistics
    processed_count = 0
    action_count = 0
    unknown_count = 0
    reason_counts: Dict[str, int] = {}
    specific_counter: Dict[str, int] = {}
    general_counter: Dict[str, int] = {}
    csv_records: List[Dict[str, str]] = []

    file_op = copy_file if args.mode == "copy" else move_file

    for idx, src_file in enumerate(files, 1):
        # Skip if file is already inside destination (avoid recursion)
        if is_inside_dest(src_file, dest_dir):
            if args.debug:
                print(f"[DEBUG] Skipping (already in dest): {src_file}")
            continue

        # Classify
        specific, general, reason = classify_file(src_file, level=args.level, debug=args.debug)

        # Skip check for unknown-only mode
        if not should_process_file(src_file, dest_dir, args.skip_unknown_only, (specific, general, reason)):
            if args.debug:
                print(f"[DEBUG] Skipping (not unknown): {src_file}")
            continue

        # Increment reason counter
        reason_counts[reason] = reason_counts.get(reason, 0) + 1

        # Update genre counters
        if specific == "Unknown":
            unknown_count += 1
        else:
            specific_counter[specific] = specific_counter.get(specific, 0) + 1
            general_counter[general] = general_counter.get(general, 0) + 1

        # Compute destination
        dest_path = compute_destination(
            src_file,
            dest_dir,
            specific,
            general,
            args.level,
        )

        # Perform file operation
        success, final_dest = file_op(src_file, dest_path, dry_run=args.dry_run)
        if success or args.dry_run:
            processed_count += 1
            action_count += 1
            if args.dry_run:
                # In dry-run, final_dest is the intended path (not actually created)
                pass
        else:
            # File operation failed; still count as processed (attempted)
            processed_count += 1

        # Record for CSV
        csv_records.append({
            "source_path": src_file,
            "detected_specific_genre": specific,
            "detected_general_genre": general,
            "classification_reason": reason,
            "destination_path": final_dest if success else f"ERROR: {final_dest}",
        })

        # Progress indicator
        if idx % 100 == 0 or idx == total_files:
            print(f"Processed {idx}/{total_files}...", end="\r")

    print("\n")  # newline after progress

    # Write CSV report
    if args.report:
        write_csv_report(args.report, csv_records, debug=args.debug)

    # Print summary
    print_summary(
        total=total_files,
        processed=processed_count,
        moved_or_copied=action_count,
        unknown_count=unknown_count,
        reason_counts=reason_counts,
        specific_counter=Counter(specific_counter),
        general_counter=Counter(general_counter),
    )


if __name__ == "__main__":
    main()
