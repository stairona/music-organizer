"""
Tests for Spotify store functions (SQLite).
"""

import json
import os
import pytest
import sqlite3
from datetime import datetime, timezone
from app.backend.store import (
    _get_spotify_conn,
    _init_spotify_db,
    get_oauth_tokens,
    save_oauth_tokens,
    delete_oauth_tokens,
    create_download_task,
    get_download_task,
    update_download_task,
    list_download_tasks,
    delete_download_task,
    cancel_download_task,
    add_progress_snapshot,
    get_progress_history,
    clear_progress_history,
    SPOTIFY_DB_PATH,
)


@pytest.fixture(autouse=True)
def isolate_spotify_db(tmp_path, monkeypatch):
    """Isolate Spotify DB to a temporary file for each test."""
    temp_db = tmp_path / "spotify_test.db"
    monkeypatch.setattr("app.backend.store.SPOTIFY_DB_PATH", str(temp_db))
    _init_spotify_db()
    yield
    # Cleanup automatic via tmp_path


class TestOAuthStore:
    """Tests for OAuth token storage."""

    def test_save_and_get_tokens(self):
        save_oauth_tokens(
            access_token="access123",
            refresh_token="refresh456",
            expires_at=1700000000,
        )
        tokens = get_oauth_tokens()
        assert tokens is not None
        assert tokens["access_token"] == "access123"
        assert tokens["refresh_token"] == "refresh456"
        assert tokens["expires_at"] == 1700000000

    def test_get_tokens_when_not_exist_returns_none(self):
        tokens = get_oauth_tokens()
        assert tokens is None

    def test_update_tokens_overwrites(self):
        save_oauth_tokens("v1", "r1", 1700000000)
        save_oauth_tokens("v2", "r2", 1700001000)
        tokens = get_oauth_tokens()
        assert tokens["access_token"] == "v2"
        assert tokens["refresh_token"] == "r2"

    def test_delete_oauth_tokens(self):
        save_oauth_tokens("a", "r", 1700000000)
        delete_oauth_tokens()
        assert get_oauth_tokens() is None


class TestDownloadTaskStore:
    """Tests for download task CRUD operations."""

    def test_create_download_task(self):
        create_download_task(
            task_id="task-1",
            playlist_id="pl-1",
            playlist_name="Test Playlist",
            destination="/tmp/music",
            total_tracks=10,
            auto_organize=True,
        )
        task = get_download_task("task-1")
        assert task is not None
        assert task["task_id"] == "task-1"
        assert task["status"] == "queued"
        assert task["total_tracks"] == 10
        assert task["completed_tracks"] == 0
        assert task["auto_organize"] == 1

    def test_get_nonexistent_task_returns_none(self):
        assert get_download_task("missing") is None

    def test_update_download_task_partial(self):
        create_download_task(
            task_id="t1",
            playlist_id="p1",
            playlist_name="P",
            destination="/d",
            total_tracks=5,
        )
        update_download_task("t1", {"status": "downloading", "progress_percent": 10.0})
        task = get_download_task("t1")
        assert task["status"] == "downloading"
        assert task["progress_percent"] == 10.0
        # Other fields unchanged
        assert task["total_tracks"] == 5

    def test_update_multiple_fields(self):
        create_download_task(
            task_id="t2",
            playlist_id="p2",
            playlist_name="P2",
            destination="/d2",
            total_tracks=8,
        )
        update_download_task(
            "t2",
            {
                "status": "completed",
                "completed_tracks": 8,
                "progress_percent": 100.0,
                "spotdl_pid": 999,
                "organize_run_id": "run-abc",
            },
        )
        task = get_download_task("t2")
        assert task["status"] == "completed"
        assert task["completed_tracks"] == 8
        assert task["spotdl_pid"] == 999
        assert task["organize_run_id"] == "run-abc"

    def test_list_download_tasks_ordered_by_created(self):
        import time
        now = int(datetime.now(timezone.utc).timestamp())

        # Create tasks with slight delay to ensure ordering
        create_download_task("t1", "p1", "P1", "/d1", 1, created_at=now)
        time.sleep(0.01)
        create_download_task("t2", "p2", "P2", "/d2", 2, created_at=now + 10)
        time.sleep(0.01)
        create_download_task("t3", "p3", "P3", "/d3", 3, created_at=now + 5)

        tasks = list_download_tasks(limit=10)
        assert len(tasks) == 3
        # Should be most recent first: t2, t3, t1
        assert tasks[0]["task_id"] == "t2"
        assert tasks[1]["task_id"] == "t3"
        assert tasks[2]["task_id"] == "t1"

    def test_list_with_status_filter(self):
        create_download_task("t1", "p1", "P1", "/d", 1)
        create_download_task("t2", "p2", "P2", "/d", 1)
        update_download_task("t1", {"status": "completed"})

        all_tasks = list_download_tasks(10)
        completed = list_download_tasks(10, status_filter="completed")
        assert len(all_tasks) == 2
        assert len(completed) == 1
        assert completed[0]["task_id"] == "t1"

    def test_delete_download_task(self):
        create_download_task("t1", "p1", "P1", "/d", 1)
        assert get_download_task("t1") is not None
        delete_download_task("t1")
        assert get_download_task("t1") is None

    def test_cancel_download_task(self):
        create_download_task("t1", "p1", "P1", "/d", 1)
        cancel_download_task("t1")
        task = get_download_task("t1")
        assert task["status"] == "cancelled"

    def test_cascade_delete_progress_history_on_task_delete(self):
        create_download_task("t1", "p1", "P1", "/d", 1)
        add_progress_snapshot("t1", 50.0, "track", 5, 10)
        history = get_progress_history("t1")
        assert len(history) == 1
        delete_download_task("t1")
        history = get_progress_history("t1")
        assert len(history) == 0  # cascade worked


class TestProgressSnapshotStore:
    """Tests for progress history operations."""

    def test_add_and_get_progress(self):
        create_download_task(
            task_id="t1",
            playlist_id="p1",
            playlist_name="P1",
            destination="/d",
            total_tracks=10,
        )
        add_progress_snapshot(
            task_id="t1",
            percent=25.0,
            current_track="Track 3",
            completed_tracks=2,
            total_tracks=10,
            errors=[],
        )
        add_progress_snapshot(
            task_id="t1",
            percent=50.0,
            current_track="Track 6",
            completed_tracks=5,
            total_tracks=10,
            errors=["timeout"],
        )
        history = get_progress_history("t1")
        assert len(history) == 2
        # Ordered by timestamp ascending
        assert history[0]["percent"] == 25.0
        assert history[1]["percent"] == 50.0
        assert history[1]["errors"] == ["timeout"]

    def test_progress_snapshot_errors_json_parsed(self):
        create_download_task(
            task_id="t1",
            playlist_id="p1",
            playlist_name="P1",
            destination="/d",
            total_tracks=5,
        )
        add_progress_snapshot(
            task_id="t1",
            percent=0.0,
            current_track="",
            completed_tracks=0,
            total_tracks=5,
            errors=["error1", "error2"],
        )
        history = get_progress_history("t1")
        assert history[0]["errors"] == ["error1", "error2"]

    def test_clear_progress_history(self):
        create_download_task("t1", "p1", "P1", "/d", 3)
        add_progress_snapshot("t1", 33.0, "track", 1, 3)
        add_progress_snapshot("t1", 66.0, "track", 2, 3)
        assert len(get_progress_history("t1")) == 2
        clear_progress_history("t1")
        assert len(get_progress_history("t1")) == 0

    def test_get_history_empty_for_task_without_snapshots(self):
        create_download_task("t1", "p1", "P1", "/d", 1)
        history = get_progress_history("t1")
        assert history == []

    def test_progress_timestamp_defaults_to_now(self):
        create_download_task(
            task_id="t1",
            playlist_id="p1",
            playlist_name="P1",
            destination="/d",
            total_tracks=1,
        )
        before = int(datetime.now(timezone.utc).timestamp())
        add_progress_snapshot("t1", 100.0, "last", 1, 1)
        after = int(datetime.now(timezone.utc).timestamp())
        history = get_progress_history("t1")
        ts = history[0]["timestamp"]
        assert before <= ts <= after


class TestSpotifyDbSchema:
    """Tests to verify database schema correctness."""

    def test_tables_exist(self):
        with _get_spotify_conn() as conn:
            cur = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('spotify_oauth', 'download_tasks', 'progress_history');"
            )
            tables = [row[0] for row in cur.fetchall()]
            assert set(tables) == {
                "spotify_oauth",
                "download_tasks",
                "progress_history",
            }

    def test_indexes_exist(self):
        with _get_spotify_conn() as conn:
            cur = conn.execute("SELECT name FROM sqlite_master WHERE type='index';")
            indexes = [row[0] for row in cur.fetchall()]
            assert "idx_download_tasks_created" in indexes
            assert "idx_progress_history_task_id" in indexes


class TestForeignKeyConstraints:
    """Tests for foreign key relationships."""

    def test_progress_cascade_delete(self):
        conn = _get_spotify_conn()
        try:
            create_download_task("t1", "p1", "P1", "/d", 1)
            add_progress_snapshot("t1", 50.0, "track", 5, 10)
            # Verify snapshot exists
            cur = conn.execute(
                "SELECT COUNT(*) FROM progress_history WHERE task_id = 't1';"
            )
            assert cur.fetchone()[0] == 1
            # Delete task
            delete_download_task("t1")
            # Verify cascade deletion
            cur = conn.execute(
                "SELECT COUNT(*) FROM progress_history WHERE task_id = 't1';"
            )
            assert cur.fetchone()[0] == 0
        finally:
            conn.close()
