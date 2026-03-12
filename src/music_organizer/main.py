#!/usr/bin/env python3
"""
Music Organizer – CLI for organizing music libraries by genre.

Usage examples:
  python -m music_organizer.main <src> <dest> --mode copy --level general
  python -m music_organizer.main <src> <dest> --mode move --level both --dry-run
  python -m music_organizer.main <src> <dest> --stats-only
"""

import argparse
import os
import sys
import logging
from typing import Dict, List, Tuple
from collections import Counter

# Relative imports (package structure)
from .scanner import scan_source_directory, is_inside_dest
from .classify import classify_file
from .fileops import compute_destination, copy_file, move_file, ensure_dir_exists
from .reporting import write_csv_report, print_summary


def setup_logging(debug: bool = False, quiet: bool = False) -> None:
    """Configure logging output."""
    level = logging.DEBUG if debug else (logging.WARNING if quiet else logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(message)s",  # Simple format for CLI
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def get_logger():
    """Get module logger."""
    return logging.getLogger(__name__)


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
        "--stats-only",
        action="store_true",
        help="Analyze library and print genre distribution without copying or moving any files. Destination path is still required but not used for file operations.",
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
        "--quiet",
        action="store_true",
        help="Suppress informational output; only show summary and errors.",
    )
    parser.add_argument(
        "--exclude-dir",
        action="append",
        metavar="DIR_NAME",
        help="Directory names to exclude from scanning (e.g., 'incomplete', 'temp'). Can be used multiple times.",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip files that already exist at the destination (do not rename duplicates).",
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

    # Setup logging
    setup_logging(debug=args.debug, quiet=args.quiet)
    logger = get_logger()

    src_dir = os.path.abspath(args.source)
    dest_dir = os.path.abspath(args.destination)

    if not os.path.isdir(src_dir):
        logging.error(f"Source directory does not exist: {src_dir}")
        sys.exit(1)

    # Destination existence only required for actual file operations (not stats-only)
    if not os.path.isdir(dest_dir) and not args.stats_only:
        logging.error(f"Destination directory does not exist: {dest_dir}")
        sys.exit(1)

    # Determine if we should avoid creating directories (dry-run or stats-only)
    dry_run_or_stats = args.dry_run or args.stats_only

    # Ensure destination exists only if we're actually writing files
    if not dry_run_or_stats:
        ensure_dir_exists(dest_dir)

    if args.debug:
        logging.debug(f"Source: {src_dir}")
        logging.debug(f"Destination: {dest_dir}")
        logging.debug(f"Mode: {args.mode}")
        logging.debug(f"Level: {args.level}")
        logging.debug(f"Dry run: {args.dry_run}")
        logging.debug(f"Stats only: {args.stats_only}")
        if args.limit:
            logging.debug(f"Limit: {args.limit}")
        if args.exclude_dir:
            logging.debug(f"Exclude directories: {args.exclude_dir}")
        logging.debug("Scanning files...")
    if args.stats_only:
        logging.info("Stats-only mode: no files will be copied or moved.")

    # Scan for files
    try:
        files = scan_source_directory(src_dir, limit=args.limit, debug=args.debug, exclude_dirs=args.exclude_dir)
    except Exception as e:
        logging.error(f"Error scanning source directory: {e}")
        sys.exit(1)

    total_files = len(files)
    if total_files == 0:
        logging.warning("No audio files found in source directory.")
        sys.exit(0)

    logging.info(f"Found {total_files} audio file(s). Starting organization...")

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
                logging.debug(f"Skipping (already in dest): {src_file}")
            continue

        # Classify
        specific, general, reason = classify_file(src_file, level=args.level, debug=args.debug)

        # Skip check for unknown-only mode
        if not should_process_file(src_file, dest_dir, args.skip_unknown_only, (specific, general, reason)):
            if args.debug:
                logging.debug(f"Skipping (not unknown): {src_file}")
            continue

        # Increment reason counter
        reason_counts[reason] = reason_counts.get(reason, 0) + 1

        # Update genre counters
        if specific == "Unknown":
            unknown_count += 1
        else:
            specific_counter[specific] = specific_counter.get(specific, 0) + 1
            general_counter[general] = general_counter.get(general, 0) + 1

        # Compute destination (avoid creating directories for dry-run/stats-only)
        dest_path = compute_destination(
            src_file,
            dest_dir,
            specific,
            general,
            args.level,
            create_dirs=not dry_run_or_stats,
        )

        # Check if file already exists at destination (--skip-existing)
        if args.skip_existing and os.path.exists(dest_path):
            if args.debug:
                logging.debug(f"Skipping existing: {src_file} -> {dest_path}")
            processed_count += 1
            # Still record in CSV for completeness
            csv_records.append({
                "source_path": src_file,
                "detected_specific_genre": specific,
                "detected_general_genre": general,
                "classification_reason": reason,
                "destination_path": dest_path + " (skipped - already exists)",
            })
            continue

        # Perform file operation (skip entirely if stats-only)
        if args.stats_only:
            # Stats-only: no file operations, but record intended destination
            success = True
            final_dest = dest_path
        else:
            success, final_dest = file_op(src_file, dest_path, dry_run=args.dry_run)

        if success or args.dry_run or args.stats_only:
            processed_count += 1
            if not (args.dry_run or args.stats_only):
                # Only count actual file operations (dry-run and stats-only don't copy/move)
                action_count += 1
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

        # Progress indicator (only show if not quiet)
        if not args.quiet and (idx % 100 == 0 or idx == total_files):
            logging.info(f"Processed {idx}/{total_files}...")

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
