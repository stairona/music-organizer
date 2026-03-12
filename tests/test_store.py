"""
Tests for run history store.
"""

import json
import pytest
import os
import tempfile
import shutil
from datetime import datetime, timezone
from app.backend.store import (
    create_run,
    update_run_progress,
    finalize_run,
    list_runs,
    get_run,
    get_latest_completed_run,
    undo_run,
    migration_needed,
    migrate_legacy_journal,
    _load_run_history,
    _save_run_history,
    RUN_HISTORY_PATH,
)


@pytest.fixture
def temp_run_history(tmp_path, monkeypatch):
    """Isolate run history storage to a temp directory."""
    monkeypatch.setattr(
        "app.backend.store.RUN_HISTORY_PATH",
        str(tmp_path / "run_history.json"),
    )
    yield tmp_path
    # Cleanup automatically via tmp_path


class TestRunHistoryStorage:
    def test_create_and_get_run(self, temp_run_history):
        run_id = create_run(
            source="/music",
            destination="/organized",
            options={"mode": "copy", "level": "specific"},
        )
        run = get_run(run_id)
        assert run is not None
        assert run["run_id"] == run_id
        assert run["source"] == "/music"
        assert run["destination"] == "/organized"
        assert run["status"] == "running"
        assert run["entries"] == []

    def test_update_progress_appends_entries(self, temp_run_history):
        run_id = create_run("/src", "/dst", {"mode": "copy"})
        update_run_progress(run_id, [
            {"source": "/src/a.mp3", "destination": "/dst/Artist/A.mp3"},
            {"source": "/src/b.mp3", "destination": "/dst/Artist/B.mp3"},
        ])
        run = get_run(run_id)
        assert len(run["entries"]) == 2
        assert run["entries"][0]["source"] == "/src/a.mp3"

    def test_finalize_run(self, temp_run_history):
        run_id = create_run("/src", "/dst", {"mode": "move"})
        summary = {"total": 5, "moved_or_copied": 5}
        finalize_run(run_id, summary, status="completed")
        run = get_run(run_id)
        assert run["status"] == "completed"
        assert run["summary"] == summary
        assert run["finished_at"] is not None

    def test_list_runs_ordering(self, temp_run_history):
        # Create multiple runs with different start times
        ids = []
        for i in range(5):
            run_id = create_run("/src", "/dst", {"mode": "copy"})
            ids.append(run_id)
            # Simulate finish
            finalize_run(run_id, {}, status="completed")

        # Reverse order to simulate older ones first
        runs = list_runs(limit=10)
        # Should be most recent first
        assert len(runs) == 5
        # Since we created them sequentially, later IDs should appear first
        first_id = runs[0]["run_id"]
        assert first_id == ids[-1]

    def test_list_runs_filter_status(self, temp_run_history):
        for i in range(3):
            run_id = create_run("/src", "/dst", {})
            finalize_run(run_id, {}, status="completed")
        run_id = create_run("/src", "/dst", {})
        finalize_run(run_id, {}, status="failed")

        completed = list_runs(status="completed")
        failed = list_runs(status="failed")
        assert len(completed) == 3
        assert len(failed) == 1

    def test_get_latest_completed_run(self, temp_run_history):
        # No runs
        assert get_latest_completed_run() is None

        # Create one completed
        run_id = create_run("/src", "/dst", {"mode": "copy"})
        finalize_run(run_id, {}, status="completed")
        latest = get_latest_completed_run()
        assert latest["run_id"] == run_id

        # Create another that is running (should not be returned)
        run_id2 = create_run("/src2", "/dst2", {})
        latest = get_latest_completed_run()
        # still first one
        assert latest["run_id"] == run_id

        # Complete the second one
        finalize_run(run_id2, {}, status="completed")
        latest = get_latest_completed_run()
        assert latest["run_id"] == run_id2

    def test_undo_run_reverts_copies(self, temp_run_history, monkeypatch):
        # Create a fake destination file to be removed
        run_id = create_run("/src", "/dst", {"mode": "copy"})
        update_run_progress(run_id, [
            {"source": "/src/a.mp3", "destination": str(temp_run_history / "a.mp3")},
        ])
        finalize_run(run_id, {}, status="completed")

        # Create the destination file
        dest_file = temp_run_history / "a.mp3"
        dest_file.write_text("fake content")

        result = undo_run(run_id, dry_run=False)
        assert result["reverted"] == 1
        assert result["failed"] == 0
        assert not dest_file.exists()

    def test_undo_run_dry_run(self, temp_run_history):
        run_id = create_run("/src", "/dst", {"mode": "copy"})
        update_run_progress(run_id, [
            {"source": "/src/a.mp3", "destination": str(temp_run_history / "a.mp3")},
        ])
        finalize_run(run_id, {}, status="completed")
        dest_file = temp_run_history / "a.mp3"
        dest_file.write_text("content")

        result = undo_run(run_id, dry_run=True)
        assert result["reverted"] == 1
        assert dest_file.exists()  # not actually deleted

    def test_undo_run_move_mode(self, temp_run_history):
        src_file = temp_run_history / "original.mp3"
        src_file.parent.mkdir(parents=True, exist_ok=True)
        src_file.write_text("original")
        dest_file = temp_run_history / "dest.mp3"

        run_id = create_run(str(src_file.parent), str(dest_file.parent), {"mode": "move"})
        update_run_progress(run_id, [
            {"source": str(src_file), "destination": str(dest_file)},
        ])
        finalize_run(run_id, {}, status="completed")

        # Simulate the file is at destination (it will be there from our setup)
        assert src_file.exists()
        assert not dest_file.exists()
        shutil.copy(str(src_file), str(dest_file))
        src_file.unlink()  # Remove to simulate moved

        result = undo_run(run_id, dry_run=False)
        assert result["reverted"] == 1
        # After undo, file should be restored to source
        assert src_file.exists()
        assert not dest_file.exists()

    def test_undo_nonexistent_run(self, temp_run_history):
        result = undo_run("nonexistent", dry_run=False)
        assert result["reverted"] == 0
        assert result["failed"] == 0
        assert len(result["errors"]) > 0

    def test_migration_from_legacy_journal(self, temp_run_history, monkeypatch):
        # Create legacy journal.json
        legacy_dir = temp_run_history
        legacy_path = legacy_dir / "journal.json"
        legacy_data = {
            "timestamp": "2024-01-01T00:00:00Z",
            "mode": "copy",
            "file_count": 2,
            "entries": [
                {"source": "/a.mp3", "destination": "/dst/a.mp3"},
                {"source": "/b.mp3", "destination": "/dst/b.mp3"},
            ],
        }
        with open(legacy_path, "w") as f:
            json.dump(legacy_data, f)

        # Patch both RUN_HISTORY_DIR and RUN_HISTORY_PATH to use temp_run_history
        import app.backend.store as store_mod
        monkeypatch.setattr(store_mod, "RUN_HISTORY_DIR", str(temp_run_history))
        monkeypatch.setattr(store_mod, "RUN_HISTORY_PATH", str(temp_run_history / "run_history.json"))

        assert migration_needed() is True

        migrated = migrate_legacy_journal()
        assert migrated is True

        # Run history should now contain the migrated run
        history = _load_run_history()
        assert len(history["runs"]) == 1
        run = history["runs"][0]
        assert run["status"] == "completed"
        assert run["options"]["mode"] == "copy"
        assert len(run["entries"]) == 2

    def test_migration_not_needed_if_no_legacy(self, temp_run_history, monkeypatch):
        import app.backend.store as store_mod
        monkeypatch.setattr(store_mod, "RUN_HISTORY_DIR", str(temp_run_history))
        monkeypatch.setattr(store_mod, "RUN_HISTORY_PATH", str(temp_run_history / "run_history.json"))
        assert migration_needed() is False
        assert migrate_legacy_journal() is False
