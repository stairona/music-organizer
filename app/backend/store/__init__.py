"""
Run history storage layer — append-only registry for organize runs.
"""

import json
import os
import shutil
import logging
import sqlite3
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from uuid import uuid4

logger = logging.getLogger(__name__)

# Store location
RUN_HISTORY_DIR = os.path.join(
    os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config")),
    "music-organizer",
)
RUN_HISTORY_PATH = os.path.join(RUN_HISTORY_DIR, "run_history.json")
LEGACY_JOURNAL_PATH = os.path.join(RUN_HISTORY_DIR, "journal.json")
LEGACY_MIGRATED_PATH = os.path.join(RUN_HISTORY_DIR, "journal.legacy-migrated.json")

# Spotify integration database (separate from run history)
SPOTIFY_DB_PATH = os.path.join(RUN_HISTORY_DIR, "spotify.db")


def _get_spotify_conn() -> sqlite3.Connection:
    """Get a connection to the Spotify SQLite database."""
    conn = sqlite3.connect(SPOTIFY_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")  # Enable cascade deletes
    return conn


def _init_spotify_db() -> None:
    """Create Spotify tables if they don't exist."""
    with _get_spotify_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS spotify_oauth (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                access_token TEXT NOT NULL,
                refresh_token TEXT NOT NULL,
                expires_at INTEGER NOT NULL,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS download_tasks (
                task_id TEXT PRIMARY KEY,
                playlist_id TEXT NOT NULL,
                playlist_name TEXT NOT NULL,
                destination TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('queued', 'downloading', 'completed', 'failed', 'cancelled')),
                started_at INTEGER,
                finished_at INTEGER,
                total_tracks INTEGER NOT NULL,
                completed_tracks INTEGER NOT NULL DEFAULT 0,
                auto_organize BOOLEAN NOT NULL DEFAULT 1,
                organize_run_id TEXT,
                error_message TEXT,
                spotdl_pid INTEGER,
                progress_percent REAL NOT NULL DEFAULT 0.0,
                current_track TEXT,
                created_at INTEGER NOT NULL
            );
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_download_tasks_created
            ON download_tasks(created_at DESC);
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS progress_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                percent REAL NOT NULL,
                current_track TEXT NOT NULL,
                completed_tracks INTEGER NOT NULL,
                total_tracks INTEGER NOT NULL,
                errors TEXT,
                FOREIGN KEY (task_id) REFERENCES download_tasks(task_id) ON DELETE CASCADE
            );
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_progress_history_task_id
            ON progress_history(task_id);
            """
        )
        conn.commit()


def _ensure_store_exists() -> None:
    """Create store directory and initialize empty run history if needed."""
    os.makedirs(RUN_HISTORY_DIR, exist_ok=True)
    if not os.path.exists(RUN_HISTORY_PATH):
        with open(RUN_HISTORY_PATH, "w", encoding="utf-8") as f:
            json.dump({"runs": []}, f, indent=2, ensure_ascii=False)
    # Initialize Spotify DB on first access
    _init_spotify_db()


def _load_run_history() -> Dict[str, List[Dict[str, Any]]]:
    """Load the run history from disk."""
    _ensure_store_exists()
    try:
        with open(RUN_HISTORY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.error(f"Failed to load run history: {e}")
        return {"runs": []}


def _save_run_history(history: Dict[str, List[Dict[str, Any]]]) -> None:
    """Save run history to disk atomically."""
    _ensure_store_exists()
    temp_path = RUN_HISTORY_PATH + ".tmp"
    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
        os.replace(temp_path, RUN_HISTORY_PATH)
    except OSError as e:
        logger.error(f"Failed to save run history: {e}")


def create_run(
    source: str,
    destination: str,
    options: Dict[str, Any],
    started_at: Optional[datetime] = None,
) -> str:
    """
    Create a new run entry with status 'running'.

    Args:
        source: Source directory
        destination: Destination directory
        options: Snapshot of all organize options (level, profile, mode, etc.)
        started_at: Optional datetime (defaults to now)

    Returns:
        run_id (UUID string)
    """
    run_id = str(uuid4())
    run_entry = {
        "run_id": run_id,
        "started_at": (started_at or datetime.now(timezone.utc)).isoformat(),
        "finished_at": None,
        "source": source,
        "destination": destination,
        "options": options,
        "summary": None,
        "status": "running",
        "entries": [],  # populated incrementally by update_run_progress
    }

    history = _load_run_history()
    history["runs"].append(run_entry)
    _save_run_history(history)

    logger.info(f"Created run {run_id}")
    return run_id


def update_run_progress(
    run_id: str,
    entries_batch: List[Dict[str, Any]],
) -> None:
    """
    Append file operation entries to a running run.

    Args:
        run_id: The run identifier
        entries_batch: List of per-file operation records to append
    """
    history = _load_run_history()
    run_entry = next((r for r in history["runs"] if r["run_id"] == run_id), None)
    if not run_entry:
        logger.error(f"Run {run_id} not found")
        return

    if run_entry["status"] != "running":
        logger.warning(f"Run {run_id} is not running (status: {run_entry['status']})")
        return

    run_entry["entries"].extend(entries_batch)
    _save_run_history(history)


def finalize_run(
    run_id: str,
    summary: Dict[str, Any],
    status: str = "completed",
    finished_at: Optional[datetime] = None,
) -> None:
    """
    Mark a run as finished (completed, cancelled, or failed).

    Args:
        run_id: Run identifier
        summary: Summary metrics (total, processed, moved_or_copied, unknown_count, etc.)
        status: One of 'completed', 'cancelled', 'failed'
        finished_at: Optional timestamp (defaults to now)
    """
    history = _load_run_history()
    run_entry = next((r for r in history["runs"] if r["run_id"] == run_id), None)
    if not run_entry:
        logger.error(f"Run {run_id} not found")
        return

    run_entry["status"] = status
    run_entry["finished_at"] = (finished_at or datetime.now(timezone.utc)).isoformat()
    run_entry["summary"] = summary

    _save_run_history(history)
    logger.info(f"Finalized run {run_id} with status {status}")


def list_runs(
    limit: int = 10,
    status: Optional[str] = None,
    since: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    """
    List recent runs, optionally filtered.

    Args:
        limit: Max number of runs to return (most recent first)
        status: Filter by status (running/completed/cancelled/failed)
        since: Only runs started after this datetime

    Returns:
        List of run entries (without full entries list to keep lightweight)
    """
    history = _load_run_history()
    runs = history["runs"]

    if status:
        runs = [r for r in runs if r.get("status") == status]
    if since:
        since_str = since.isoformat()
        runs = [r for r in runs if r.get("started_at", "") >= since_str]

    # Sort by started_at descending (most recent first)
    runs.sort(key=lambda r: r.get("started_at", ""), reverse=True)

    # Return lightweight summaries (omit full entries)
    lightweight = []
    for run in runs[:limit]:
        entry = {
            "run_id": run["run_id"],
            "started_at": run["started_at"],
            "finished_at": run.get("finished_at"),
            "source": run["source"],
            "destination": run["destination"],
            "status": run["status"],
            "options": run.get("options", {}),
        }
        if run.get("summary"):
            entry["summary"] = run["summary"]
        lightweight.append(entry)

    return lightweight


def get_run(run_id: str) -> Optional[Dict[str, Any]]:
    """
    Get full run details including per-file entries.

    Args:
        run_id: Run identifier

    Returns:
        Full run entry dict or None if not found
    """
    history = _load_run_history()
    for run in history["runs"]:
        if run["run_id"] == run_id:
            return run
    return None


def get_latest_completed_run() -> Optional[Dict[str, Any]]:
    """
    Get the most recent completed run (for undo compatibility).

    Returns:
        Most recent completed run or None
    """
    runs = list_runs(limit=20, status="completed")
    return runs[0] if runs else None


def undo_run(run_id: str, dry_run: bool = False) -> Dict[str, Any]:
    """
    Undo a specific run by reversing all file operations.

    Args:
        run_id: Run identifier
        dry_run: If True, show what would be undone without doing it

    Returns:
        Dict with undo results: {"reverted": int, "failed": int, "errors": []}
    """
    run_entry = get_run(run_id)
    if not run_entry:
        logger.error(f"Run {run_id} not found")
        return {"reverted": 0, "failed": 0, "errors": [f"Run {run_id} not found"]}

    if run_entry["status"] != "completed":
        logger.warning(f"Run {run_id} status is {run_entry['status']}, not completed")
        return {"reverted": 0, "failed": 0, "errors": [f"Run status: {run_entry['status']}"]}

    mode = run_entry.get("options", {}).get("mode", "copy")
    entries = run_entry.get("entries", [])

    reverted = 0
    failed = 0
    errors = []

    for entry in entries:
        dest = entry.get("destination", "")
        src = entry.get("source", "")

        if not dest or not os.path.exists(dest):
            continue

        if mode == "copy":
            if dry_run:
                reverted += 1
                continue
            try:
                os.remove(dest)
                reverted += 1
            except OSError as e:
                failed += 1
                errors.append(str(e))
        elif mode == "move":
            if dry_run:
                reverted += 1
                continue
            if not src:
                logger.warning(f"Skip (no original path): {dest}")
                continue
            try:
                os.makedirs(os.path.dirname(src), exist_ok=True)
                shutil.move(dest, src)
                reverted += 1
            except OSError as e:
                failed += 1
                errors.append(str(e))
        else:
            # Unknown mode, skip
            continue

    if not dry_run and reverted > 0:
        history = _load_run_history()
        run_entry_mut = next((r for r in history["runs"] if r["run_id"] == run_id), None)
        if run_entry_mut:
            run_entry_mut["status"] = "undone"
            run_entry_mut["undone_at"] = datetime.now(timezone.utc).isoformat()
            run_entry_mut["undo_result"] = {
                "reverted": reverted,
                "failed": failed,
                "errors": errors,
            }
            _save_run_history(history)

    return {
        "reverted": reverted,
        "failed": failed,
        "errors": errors,
    }


def migration_needed() -> bool:
    """Check if legacy journal.json exists and needs migration."""
    return os.path.exists(LEGACY_JOURNAL_PATH)


def migrate_legacy_journal() -> bool:
    """
    Migrate old single-journal format to new run history.

    Returns:
        True if migration performed, False otherwise
    """
    if not os.path.exists(LEGACY_JOURNAL_PATH):
        return False

    try:
        with open(LEGACY_JOURNAL_PATH, "r", encoding="utf-8") as f:
            legacy = json.load(f)

        if not legacy:
            return False

        # Create a run entry from legacy journal
        run_id = str(uuid4())
        run_entry = {
            "run_id": run_id,
            "started_at": legacy.get("timestamp"),
            "finished_at": legacy.get("timestamp"),
            "source": "",  # Legacy doesn't track source/dest separately
            "destination": "",
            "options": {"mode": legacy.get("mode", "copy")},
            "summary": {
                "total": legacy.get("file_count", 0),
                "processed": legacy.get("file_count", 0),
                "moved_or_copied": legacy.get("file_count", 0),
                "unknown_count": 0,
            },
            "status": "completed",
            "entries": legacy.get("entries", []),
        }

        history = _load_run_history()
        history["runs"].append(run_entry)
        _save_run_history(history)

        # Archive the legacy file so migration is one-time and auditable.
        os.replace(LEGACY_JOURNAL_PATH, LEGACY_MIGRATED_PATH)

        logger.info(f"Migrated legacy journal to run {run_id}")
        return True

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return False


# ==================== Spotify OAuth Functions ====================


def get_oauth_tokens() -> Optional[Dict[str, Any]]:
    """
    Retrieve stored OAuth tokens.

    Returns:
        Dict with access_token, refresh_token, expires_at, or None if not stored
    """
    with _get_spotify_conn() as conn:
        cur = conn.execute(
            "SELECT access_token, refresh_token, expires_at FROM spotify_oauth WHERE id = 1;"
        )
        row = cur.fetchone()
        if row:
            return dict(row)
        return None


def save_oauth_tokens(
    access_token: str,
    refresh_token: str,
    expires_at: int,
    created_at: Optional[int] = None,
) -> None:
    """
    Store OAuth tokens, upserting the single row (id=1).

    Args:
        access_token: Spotify access token
        refresh_token: Spotify refresh token
        expires_at: Unix timestamp when access token expires
        created_at: Unix timestamp (defaults to now)
    """
    now = int(datetime.now(timezone.utc).timestamp())
    created_at = created_at or now

    with _get_spotify_conn() as conn:
        conn.execute(
            """
            INSERT INTO spotify_oauth (id, access_token, refresh_token, expires_at, created_at, updated_at)
            VALUES (1, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                access_token = excluded.access_token,
                refresh_token = excluded.refresh_token,
                expires_at = excluded.expires_at,
                updated_at = excluded.updated_at;
            """,
            (access_token, refresh_token, expires_at, created_at, now),
        )
        conn.commit()


def delete_oauth_tokens() -> None:
    """Delete stored OAuth tokens (logout)."""
    with _get_spotify_conn() as conn:
        conn.execute("DELETE FROM spotify_oauth WHERE id = 1;")
        conn.commit()


# ==================== Download Task Functions ====================


def create_download_task(
    task_id: str,
    playlist_id: str,
    playlist_name: str,
    destination: str,
    total_tracks: int,
    auto_organize: bool = True,
    created_at: Optional[int] = None,
) -> None:
    """Create a new download task in 'queued' status."""
    now = int(datetime.now(timezone.utc).timestamp())
    created_at = created_at or now

    with _get_spotify_conn() as conn:
        conn.execute(
            """
            INSERT INTO download_tasks (
                task_id, playlist_id, playlist_name, destination, status,
                total_tracks, auto_organize, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                task_id,
                playlist_id,
                playlist_name,
                destination,
                "queued",
                total_tracks,
                1 if auto_organize else 0,
                created_at,
            ),
        )
        conn.commit()


def get_download_task(task_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve a download task by ID."""
    with _get_spotify_conn() as conn:
        cur = conn.execute("SELECT * FROM download_tasks WHERE task_id = ?;", (task_id,))
        row = cur.fetchone()
        if row:
            return dict(row)
        return None


def update_download_task(task_id: str, updates: Dict[str, Any]) -> None:
    """
    Update specific fields of a download task.

    Args:
        task_id: Task identifier
        updates: Dict of column names to new values
    """
    if not updates:
        return

    set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
    values = list(updates.values())
    values.append(task_id)

    with _get_spotify_conn() as conn:
        conn.execute(
            f"UPDATE download_tasks SET {set_clause} WHERE task_id = ?;", values
        )
        conn.commit()


def list_download_tasks(
    limit: int = 50, status_filter: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    List download tasks, most recent first.

    Args:
        limit: Maximum number of tasks to return
        status_filter: Optional status to filter by

    Returns:
        List of task dicts
    """
    with _get_spotify_conn() as conn:
        query = "SELECT * FROM download_tasks"
        params = []
        if status_filter:
            query += " WHERE status = ?"
            params.append(status_filter)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        cur = conn.execute(query, params)
        rows = cur.fetchall()
        return [dict(row) for row in rows]


def delete_download_task(task_id: str) -> None:
    """Delete a download task (and cascade its progress history)."""
    with _get_spotify_conn() as conn:
        conn.execute("DELETE FROM download_tasks WHERE task_id = ?;", (task_id,))
        conn.commit()


def cancel_download_task(task_id: str) -> None:
    """Mark a task as cancelled."""
    update_download_task(task_id, {"status": "cancelled"})


# ==================== Progress Snapshot Functions ====================


def add_progress_snapshot(
    task_id: str,
    percent: float,
    current_track: str,
    completed_tracks: int,
    total_tracks: int,
    errors: Optional[List[str]] = None,
    timestamp: Optional[int] = None,
) -> None:
    """
    Add a progress snapshot for a task.

    Args:
        task_id: Task identifier
        percent: Progress percentage (0-100)
        current_track: Currently downloading track name
        completed_tracks: Number of tracks completed
        total_tracks: Total tracks in playlist
        errors: Optional list of error messages
        timestamp: Unix timestamp (defaults to now)
    """
    now = int(datetime.now(timezone.utc).timestamp())
    timestamp = timestamp or now
    errors_json = json.dumps(errors or [])

    with _get_spotify_conn() as conn:
        conn.execute(
            """
            INSERT INTO progress_history (task_id, timestamp, percent, current_track, completed_tracks, total_tracks, errors)
            VALUES (?, ?, ?, ?, ?, ?, ?);
            """,
            (
                task_id,
                timestamp,
                percent,
                current_track,
                completed_tracks,
                total_tracks,
                errors_json,
            ),
        )
        conn.commit()


def get_progress_history(task_id: str) -> List[Dict[str, Any]]:
    """Retrieve all progress snapshots for a task, ordered by timestamp ascending."""
    with _get_spotify_conn() as conn:
        cur = conn.execute(
            "SELECT * FROM progress_history WHERE task_id = ? ORDER BY timestamp ASC;",
            (task_id,),
        )
        rows = cur.fetchall()
        snapshots = []
        for row in rows:
            snap = dict(row)
            # Parse errors JSON
            try:
                snap["errors"] = json.loads(snap.get("errors", "[]"))
            except json.JSONDecodeError:
                snap["errors"] = []
            snapshots.append(snap)
        return snapshots


def clear_progress_history(task_id: str) -> None:
    """Delete all progress snapshots for a task."""
    with _get_spotify_conn() as conn:
        conn.execute(
            "DELETE FROM progress_history WHERE task_id = ?;",
            (task_id,),
        )
        conn.commit()
