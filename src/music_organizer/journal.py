"""
Journal system — records file operations so they can be undone.

Stores a JSON log at ~/.config/music-organizer/journal.json
"""

import json
import os
import shutil
import logging
from datetime import datetime, timezone
from typing import Dict, List

logger = logging.getLogger(__name__)

JOURNAL_DIR = os.path.join(
    os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config")),
    "music-organizer",
)
JOURNAL_PATH = os.path.join(JOURNAL_DIR, "journal.json")


def save_journal(entries: List[Dict[str, str]], mode: str) -> None:
    """Save a journal of the organize operation for undo."""
    os.makedirs(JOURNAL_DIR, exist_ok=True)

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "file_count": len(entries),
        "entries": entries,
    }

    # Keep only the last operation (simple undo)
    with open(JOURNAL_PATH, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)

    logger.info(f"Journal saved: {len(entries)} operations → {JOURNAL_PATH}")


def load_journal() -> dict:
    """Load the last journal. Returns empty dict if none exists."""
    if not os.path.exists(JOURNAL_PATH):
        return {}
    with open(JOURNAL_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def undo_last() -> int:
    """
    Undo the last organize operation.

    For copy mode: deletes the copies at destination.
    For move mode: moves files back to their original location.

    Returns the number of files successfully reverted.
    """
    journal = load_journal()
    if not journal:
        logger.warning("No journal found. Nothing to undo.")
        return 0

    mode = journal.get("mode", "copy")
    entries = journal.get("entries", [])
    timestamp = journal.get("timestamp", "unknown")

    logger.info(f"Undoing {len(entries)} {mode} operations from {timestamp}")

    reverted = 0
    for entry in entries:
        src = entry.get("source", "")
        dest = entry.get("destination", "")

        if not dest or not os.path.exists(dest):
            logger.warning(f"  Skip (destination missing): {dest}")
            continue

        if mode == "copy":
            # Undo copy = delete the copy
            try:
                os.remove(dest)
                reverted += 1
            except OSError as e:
                logger.error(f"  Failed to remove {dest}: {e}")
        elif mode == "move":
            # Undo move = move back to original location
            if not src:
                logger.warning(f"  Skip (no original path recorded): {dest}")
                continue
            try:
                os.makedirs(os.path.dirname(src), exist_ok=True)
                shutil.move(dest, src)
                reverted += 1
            except OSError as e:
                logger.error(f"  Failed to restore {dest} → {src}: {e}")

    # Clear journal after undo
    if os.path.exists(JOURNAL_PATH):
        os.remove(JOURNAL_PATH)

    logger.info(f"Reverted {reverted}/{len(entries)} files.")
    return reverted
