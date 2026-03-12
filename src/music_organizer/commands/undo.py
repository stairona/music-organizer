"""
undo command — revert the last organize operation.
"""

import logging
import sys

from ..journal import undo_last, load_journal


def run_undo(args) -> None:
    """Execute the undo subcommand."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")

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

    reverted = undo_last()
    print(f"\nDone. Reverted {reverted} files.")
