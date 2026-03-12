"""
analyze command — scan a music library and print genre distribution.

No files are copied or moved.
"""

import logging
import os
import sys
from collections import Counter
from typing import Dict, List

from ..scanner import scan_source_directory
from ..classify import classify_file
from ..reporting import write_csv_report, print_summary


def _setup_logging(debug: bool = False, quiet: bool = False) -> None:
    level = logging.DEBUG if debug else (logging.WARNING if quiet else logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def run_analyze(args) -> None:
    """Execute the analyze subcommand."""
    _setup_logging(debug=args.debug, quiet=args.quiet)

    src_dir = os.path.abspath(args.source)
    if not os.path.isdir(src_dir):
        logging.error(f"Source directory does not exist: {src_dir}")
        sys.exit(1)

    logging.info(f"Analyzing: {src_dir}")

    try:
        files = scan_source_directory(
            src_dir,
            limit=args.limit,
            debug=args.debug,
            exclude_dirs=args.exclude_dir,
        )
    except Exception as e:
        logging.error(f"Error scanning source directory: {e}")
        sys.exit(1)

    total_files = len(files)
    if total_files == 0:
        logging.warning("No audio files found.")
        sys.exit(0)

    logging.info(f"Found {total_files} audio file(s). Classifying...")

    unknown_count = 0
    reason_counts: Counter = Counter()
    specific_counter: Counter = Counter()
    general_counter: Counter = Counter()
    csv_records: List[Dict[str, str]] = []

    for idx, src_file in enumerate(files, 1):
        specific, general, reason = classify_file(
            src_file, level=args.level, debug=args.debug
        )

        reason_counts[reason] += 1

        if specific == "Unknown":
            unknown_count += 1
        else:
            specific_counter[specific] += 1
            general_counter[general] += 1

        csv_records.append({
            "source_path": src_file,
            "detected_specific_genre": specific,
            "detected_general_genre": general,
            "classification_reason": reason,
            "destination_path": "(analyze only)",
        })

        if not args.quiet and (idx % 100 == 0 or idx == total_files):
            logging.info(f"Classified {idx}/{total_files}...")

    if hasattr(args, "report") and args.report:
        write_csv_report(args.report, csv_records, debug=args.debug)

    print_summary(
        total=total_files,
        processed=total_files,
        moved_or_copied=0,
        unknown_count=unknown_count,
        reason_counts=reason_counts,
        specific_counter=specific_counter,
        general_counter=general_counter,
    )
