"""
organize command — copy or move music files into genre-based folder structure.
"""

import logging
import os
import sys
from collections import Counter
from typing import Dict, List, Tuple

from ..scanner import scan_source_directory, is_inside_dest
from ..classify import classify_file
from ..fileops import compute_destination, copy_file, move_file, ensure_dir_exists
from ..reporting import write_csv_report, print_summary


def _setup_logging(debug: bool = False, quiet: bool = False) -> None:
    level = logging.DEBUG if debug else (logging.WARNING if quiet else logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def _should_process_file(
    skip_unknown_only: bool,
    classification: Tuple[str, str, str],
) -> bool:
    if not skip_unknown_only:
        return True
    specific, general, reason = classification
    return specific == "Unknown" or general == "Other / Unknown"


def run_organize(args) -> None:
    """Execute the organize subcommand."""
    # If interactive mode requested, hand off to prompts
    if getattr(args, "interactive", False):
        from .interactive import run_interactive
        run_interactive(args)
        return

    # Apply preset if specified (non-interactive only)
    if getattr(args, "preset", None):
        from ..presets import get_preset
        try:
            preset = get_preset(args.preset)
            args.level = preset["level"]
            args.profile = preset["profile"]
        except ValueError as e:
            logging.error(str(e))
            sys.exit(1)

    _setup_logging(debug=args.debug, quiet=args.quiet)

    src_dir = os.path.abspath(args.source)
    dest_dir = os.path.abspath(args.destination)

    if not os.path.isdir(src_dir):
        logging.error(f"Source directory does not exist: {src_dir}")
        sys.exit(1)

    dry_run = args.dry_run

    if not dry_run:
        ensure_dir_exists(dest_dir)

    logging.info(f"Source: {src_dir}")
    logging.info(f"Destination: {dest_dir}")
    logging.info(f"Mode: {args.mode} | Level: {args.level} | Dry run: {dry_run}")

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
        logging.warning("No audio files found in source directory.")
        sys.exit(0)

    logging.info(f"Found {total_files} audio file(s). Starting organization...")

    processed_count = 0
    action_count = 0
    unknown_count = 0
    reason_counts: Counter = Counter()
    specific_counter: Counter = Counter()
    general_counter: Counter = Counter()
    csv_records: List[Dict[str, str]] = []
    journal_entries: List[Dict[str, str]] = []
    # Track folder counts for CDJ-safe profile (warn if >500 files per folder)
    folder_counts: Counter = Counter()

    file_op = copy_file if args.mode == "copy" else move_file

    for idx, src_file in enumerate(files, 1):
        if is_inside_dest(src_file, dest_dir):
            continue

        specific, general, reason = classify_file(
            src_file, level=args.level, debug=args.debug
        )

        if not _should_process_file(args.skip_unknown_only, (specific, general, reason)):
            continue

        reason_counts[reason] += 1

        if specific == "Unknown":
            unknown_count += 1
        else:
            specific_counter[specific] += 1
            general_counter[general] += 1

        dest_path = compute_destination(
            src_file, dest_dir, specific, general, args.level,
            create_dirs=not dry_run,
            profile=args.profile,
        )

        if args.skip_existing and os.path.exists(dest_path):
            processed_count += 1
            csv_records.append({
                "source_path": src_file,
                "detected_specific_genre": specific,
                "detected_general_genre": general,
                "classification_reason": reason,
                "destination_path": dest_path + " (skipped - exists)",
            })
            continue

        success, final_dest = file_op(src_file, dest_path, dry_run=dry_run)

        if success or dry_run:
            processed_count += 1
            if not dry_run:
                action_count += 1
                journal_entries.append({
                    "source": src_file,
                    "destination": final_dest,
                    "mode": args.mode,
                })
            # Track folder count for CDJ-safe profile
            dest_dir_final = os.path.dirname(final_dest)
            folder_counts[dest_dir_final] += 1
        else:
            processed_count += 1

        csv_records.append({
            "source_path": src_file,
            "detected_specific_genre": specific,
            "detected_general_genre": general,
            "classification_reason": reason,
            "destination_path": final_dest if success else f"ERROR: {final_dest}",
        })

        if not args.quiet and (idx % 100 == 0 or idx == total_files):
            logging.info(f"Processed {idx}/{total_files}...")

    # CDJ-safe: warn if any folder exceeds 500 files
    if args.profile == "cdj-safe":
        for folder, count in folder_counts.items():
            if count > 500:
                logging.warning(f"CDJ-safe: Folder exceeds 500 files ({count} new files): {folder}")

    # Save journal for undo (only if we actually moved/copied files)
    if journal_entries and not dry_run:
        try:
            from ..journal import save_journal
            save_journal(journal_entries, args.mode)
        except Exception as e:
            logging.warning(f"Could not save undo journal: {e}")

    if hasattr(args, "report") and args.report:
        write_csv_report(args.report, csv_records, debug=args.debug)

    print_summary(
        total=total_files,
        processed=processed_count,
        moved_or_copied=action_count,
        unknown_count=unknown_count,
        reason_counts=reason_counts,
        specific_counter=specific_counter,
        general_counter=general_counter,
    )
