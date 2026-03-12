"""
Service orchestration layer for music organizer operations.
"""

from ..models import AnalyzeResult, OrganizeResult, RunSummary, UnknownDiagnostics, FileOperation
from ..store import create_run, update_run_progress, finalize_run
from music_organizer.scanner import scan_source_directory, is_inside_dest
from music_organizer.classify import classify_file
from music_organizer.fileops import compute_destination, copy_file, move_file, ensure_dir_exists
from music_organizer.reporting import write_csv_report
from collections import Counter
from typing import Dict, List
import os
import sys
from datetime import datetime, timezone


def _should_process_file(
    skip_unknown_only: bool,
    classification: tuple,
) -> bool:
    if not skip_unknown_only:
        return True
    specific, general, reason = classification
    return specific == "Unknown" or general == "Other / Unknown"


def analyze_service(
    source: str,
    level: str = "general",
    limit: int = None,
    exclude_dir: List[str] = None,
    debug: bool = False,
    report_path: str = None,
) -> AnalyzeResult:
    src_dir = os.path.abspath(source)
    if not os.path.isdir(src_dir):
        raise ValueError(f"Source directory does not exist: {src_dir}")

    files = scan_source_directory(
        src_dir,
        limit=limit,
        debug=debug,
        exclude_dirs=exclude_dir,
    )

    total_files = len(files)
    if total_files == 0:
        return AnalyzeResult(
            success=True,
            summary=RunSummary(
                total=0,
                processed=0,
                moved_or_copied=0,
                unknown_count=0,
                reason_counts={},
                specific_counter={},
                general_counter={},
            ),
            unknown_diagnostics=UnknownDiagnostics(count=0, sample_paths=[]),
        )

    unknown_count = 0
    reason_counts: Counter = Counter()
    specific_counter: Counter = Counter()
    general_counter: Counter = Counter()
    unknown_sources: List[str] = []
    csv_records: List[Dict[str, str]] = []

    for src_file in files:
        specific, general, reason = classify_file(src_file, level=level, debug=debug)
        reason_counts[reason] += 1

        if specific == "Unknown":
            unknown_count += 1
            unknown_sources.append(src_file)
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

    if report_path:
        write_csv_report(report_path, csv_records, debug=debug)

    summary = RunSummary(
        total=total_files,
        processed=total_files,
        moved_or_copied=0,
        unknown_count=unknown_count,
        reason_counts=dict(reason_counts),
        specific_counter=dict(specific_counter),
        general_counter=dict(general_counter),
    )

    unknown_diag = UnknownDiagnostics(
        count=unknown_count,
        sample_paths=unknown_sources[:10],
    )

    return AnalyzeResult(
        success=True,
        summary=summary,
        unknown_diagnostics=unknown_diag,
        csv_report_path=report_path,
    )


def organize_service(
    source: str,
    destination: str,
    mode: str = "copy",
    level: str = "general",
    profile: str = "default",
    dry_run: bool = False,
    skip_existing: bool = False,
    skip_unknown_only: bool = False,
    on_collision: str = "hash",
    limit: int = None,
    exclude_dir: List[str] = None,
    debug: bool = False,
    report_path: str = None,
) -> OrganizeResult:
    src_dir = os.path.abspath(source)
    dest_dir = os.path.abspath(destination)

    if not os.path.isdir(src_dir):
        raise ValueError(f"Source directory does not exist: {src_dir}")

    if not dry_run:
        ensure_dir_exists(dest_dir)

    files = scan_source_directory(
        src_dir,
        limit=limit,
        debug=debug,
        exclude_dirs=exclude_dir,
    )

    total_files = len(files)
    if total_files == 0:
        # Finalize empty run as well
        run_id = create_run(
            source=src_dir,
            destination=dest_dir,
            options={
                "mode": mode,
                "level": level,
                "profile": profile,
                "dry_run": dry_run,
                "skip_existing": skip_existing,
                "skip_unknown_only": skip_unknown_only,
                "on_collision": on_collision,
            },
        )
        finalize_run(run_id, summary={}, status="completed")
        return OrganizeResult(
            success=True,
            summary=RunSummary(
                total=0,
                processed=0,
                moved_or_copied=0,
                unknown_count=0,
                reason_counts={},
                specific_counter={},
                general_counter={},
            ),
        )

    # Create run entry before processing
    run_id = create_run(
        source=src_dir,
        destination=dest_dir,
        options={
            "mode": mode,
            "level": level,
            "profile": profile,
            "dry_run": dry_run,
            "skip_existing": skip_existing,
            "skip_unknown_only": skip_unknown_only,
            "on_collision": on_collision,
        },
        started_at=datetime.now(timezone.utc),
    )

    processed_count = 0
    action_count = 0
    unknown_count = 0
    reason_counts: Counter = Counter()
    specific_counter: Counter = Counter()
    general_counter: Counter = Counter()
    skipped_counts: Counter = Counter()
    unknown_sources: List[str] = []
    csv_records: List[Dict[str, str]] = []
    journal_entries: List[Dict[str, str]] = []
    folder_counts: Counter = Counter()
    warnings: List[str] = []
    operation_entries: List[FileOperation] = []  # For run history

    collision_policy = "skip" if skip_existing else on_collision
    file_op = copy_file if mode == "copy" else move_file

    for src_file in files:
        if is_inside_dest(src_file, dest_dir):
            continue

        specific, general, reason = classify_file(src_file, level=level, debug=debug)

        if not _should_process_file(skip_unknown_only, (specific, general, reason)):
            continue

        reason_counts[reason] += 1

        if specific == "Unknown":
            unknown_count += 1
            unknown_sources.append(src_file)
        else:
            specific_counter[specific] += 1
            general_counter[general] += 1

        dest_path = compute_destination(
            src_file, dest_dir, specific, general, level,
            create_dirs=not dry_run,
            profile=profile,
        )

        success, final_dest, result = file_op(
            src_file,
            dest_path,
            dry_run=dry_run,
            collision_policy=collision_policy,
        )

        if success or dry_run:
            processed_count += 1
            if result in ("copied", "moved"):
                action_count += 1
                journal_entries.append({
                    "source": src_file,
                    "destination": final_dest,
                    "mode": mode,
                })
                # Record for run history
                operation_entries.append(FileOperation(
                    source=src_file,
                    destination=final_dest,
                ))
            elif result.startswith("skipped"):
                skipped_counts[result] += 1
            dest_dir_final = os.path.dirname(final_dest)
            if result in ("copied", "moved", "dry-run"):
                folder_counts[dest_dir_final] += 1

        destination_display = final_dest
        if result == "skipped-existing":
            destination_display = final_dest + " (skipped - exists)"
        elif result == "skipped-duplicate":
            destination_display = final_dest + " (skipped - duplicate content)"
        elif not success:
            destination_display = f"ERROR: {final_dest}"

        csv_records.append({
            "source_path": src_file,
            "detected_specific_genre": specific,
            "detected_general_genre": general,
            "classification_reason": reason,
            "destination_path": destination_display,
        })

    # Update run with all file operations (batch append)
    if operation_entries:
        update_run_progress(run_id, [op.model_dump() for op in operation_entries])

    # CDJ-safe warnings
    if profile == "cdj-safe":
        for folder, count in folder_counts.items():
            if count > 500:
                warnings.append(f"CDJ-safe: Folder exceeds 500 files ({count}): {folder}")

    # Save journal for undo (legacy single-run support)
    journal_saved = False
    if journal_entries and not dry_run:
        try:
            save_journal(journal_entries, mode)
            journal_saved = True
        except Exception as e:
            warnings.append(f"Could not save undo journal: {e}")

    if report_path:
        write_csv_report(report_path, csv_records, debug=debug)

    summary = RunSummary(
        total=total_files,
        processed=processed_count,
        moved_or_copied=action_count,
        unknown_count=unknown_count,
        reason_counts=dict(reason_counts),
        specific_counter=dict(specific_counter),
        general_counter=dict(general_counter),
        skipped_counts=dict(skipped_counts),
    )

    unknown_diag = UnknownDiagnostics(
        count=unknown_count,
        sample_paths=unknown_sources[:10],
    )

    # Finalize run in registry
    finalize_run(
        run_id,
        summary=summary.model_dump(),
        status="completed",
        finished_at=datetime.now(timezone.utc),
    )

    return OrganizeResult(
        success=True,
        summary=summary,
        unknown_diagnostics=unknown_diag,
        csv_report_path=report_path,
        journal_saved=journal_saved,
        warnings=warnings,
    )
