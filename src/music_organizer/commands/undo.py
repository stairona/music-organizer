"""
undo command — revert the last organize operation using run history.
"""

import logging
import sys
import shutil
import os

from ..journal import load_journal

logger = logging.getLogger(__name__)


def run_undo(args) -> None:
    """Execute the undo subcommand."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    # Try to use the new run registry if available
    try:
        from app.backend.store import get_latest_completed_run, undo_run, migration_needed, migrate_legacy_journal

        # Migrate legacy journal if needed and possible
        if migration_needed():
            if migrate_legacy_journal():
                print("Note: Migrated legacy undo journal to run history.")

        # Get latest completed run from registry
        latest = get_latest_completed_run()
        if latest:
            run_id = latest["run_id"]
            mode = latest.get("options", {}).get("mode", "copy")
            count = latest.get("summary", {}).get("moved_or_copied", 0)
            timestamp = latest.get("started_at", "unknown")

            print(f"Last operation: {mode} {count} files ({timestamp})")

            if mode == "move":
                print("WARNING: This will move files back to their original locations.")
            else:
                print("This will delete the copied files at the destination.")

            confirm = input("\nProceed with undo? [y/N] ").strip().lower()
            if confirm not in ("y", "yes"):
                print("Undo cancelled.")
                sys.exit(0)

            result = undo_run(run_id, dry_run=False)
            print(f"\nDone. Reverted {result['reverted']} files.")
            if result['failed'] > 0:
                print(f"Failed: {result['failed']} files. Errors: {', '.join(result['errors'][:3])}")
            sys.exit(0)

    except ImportError:
        # Backend store not available, fall back to legacy journal
        pass
    except Exception as e:
        logger.error(f"Error accessing run history: {e}")
        # Fall back to legacy

    # Fallback: legacy single-journal undo
    journal = load_journal()
    if not journal:
        print("No undo journal found. Nothing to revert.")
        sys.exit(0)

    mode = journal.get("mode", "copy")
    count = journal.get("file_count", 0)
    timestamp = journal.get("timestamp", "unknown")

    print(f"Last operation: {mode} {count} files ({timestamp})")

    if mode == "move":
        print("WARNING: This will move files back to their original locations.")
    else:
        print("This will delete the copied files at the destination.")

    confirm = input("\nProceed with undo? [y/N] ").strip().lower()
    if confirm not in ("y", "yes"):
        print("Undo cancelled.")
        sys.exit(0)

    from ..journal import undo_last
    reverted = undo_last()
    print(f"\nDone. Reverted {reverted} files.")
