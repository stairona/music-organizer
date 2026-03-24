"""
Tests for spotdl orchestration service.
"""

import asyncio
import sys
import time
from unittest.mock import AsyncMock, MagicMock, Mock, patch
import pytest

from app.backend.services.spotdl_service import (
    download_playlist,
    cancel_download,
    get_download_status,
    _running_processes,
    _extract_percentage,
    _extract_filename,
)
from app.backend.store import (
    create_download_task,
    update_download_task,
    add_progress_snapshot,
    get_download_task,
    get_progress_history,
)


# Helpers
def clear_running_processes():
    """Clear global process registry between tests."""
    _running_processes.clear()


class TestProgressParsers:
    """Test helper functions for parsing spotdl output."""

    def test_extract_percentage(self):
        assert _extract_percentage("[download]  50.0% of ~10.00MiB") == 50.0
        assert _extract_percentage("100%") == 100.0
        assert _extract_percentage("Progress: 75%") == 75.0
        assert _extract_percentage("No percent here") is None
        assert _extract_percentage("101%") is None  # out of range

    def test_extract_filename(self):
        assert _extract_filename("Downloaded: /path/song.mp3") == "/path/song.mp3"
        assert _extract_filename("Saving: My Song.mp3") == "My Song.mp3"
        assert _extract_filename("Processing: Track Name") == "Track Name"
        assert _extract_filename("Some random line") is None


class TestDownloadPlaylist:
    """Tests for the main download_playlist function."""

    @pytest.fixture(autouse=True)
    def isolate_globals(self):
        clear_running_processes()
        yield
        clear_running_processes()

    def test_download_successful(self):
        """Test full download flow with mocked subprocess."""
        task_id = "test-task-123"
        playlist_id = "pl123"
        destination = "/tmp/music"

        # Mock get_playlist_info
        with patch(
            "app.backend.services.spotdl_service.get_playlist_info",
            return_value={"name": "Test Playlist", "track_count": 10, "snapshot_id": "abc"},
        ), \
        patch(
            "app.backend.services.spotdl_service.update_download_task"
        ) as mock_update, \
        patch(
            "app.backend.services.spotdl_service.add_progress_snapshot"
        ) as mock_snapshot, \
        patch(
            "app.backend.services.spotdl_service.get_progress_history",
            return_value=[]
        ) as mock_history, \
        patch(
            "app.backend.services.spotify_service.get_playlist_info",  # in case it's called again
        ):
            # Mock organize_service
            with patch(
                "app.backend.services.spotdl_service.organize_service"
            ) as mock_organize, \
            patch(
                "asyncio.create_subprocess_exec", new_callable=AsyncMock
            ) as mock_subprocess:

                # Prepare mock subprocess
                mock_proc = MagicMock()
                mock_proc.pid = 12345

                # Simulate stdout: two progress lines then EOF
                outputs = [
                    b"[download]  25% of ~10.00MiB\n",
                    b"[download]  50% of ~10.00MiB\n",
                    b"",  # EOF
                ]
                mock_proc.stdout.read = AsyncMock(side_effect=outputs)
                mock_proc.wait = AsyncMock(return_value=0)  # exit code 0
                mock_subprocess.return_value = mock_proc

                # Run the async function synchronously
                asyncio.run(download_playlist(
                    playlist_id=playlist_id,
                    destination=destination,
                    task_id=task_id,
                ))

                # Verify update_download_task was called multiple times
                assert mock_update.call_count >= 2  # at least: start (downloading) and complete

                # Extract the updates dict (second positional arg) from each call and get status
                status_calls = [args[1].get("status") for args, kwargs in mock_update.call_args_list if len(args) >= 2 and "status" in args[1]]
                assert "downloading" in status_calls
                assert "completed" in status_calls

                # Verify snapshots added
                assert mock_snapshot.call_count >= 2

                # Verify organize_service called (auto_organize default True)
                mock_organize.assert_called_once()

    def test_download_fails_on_nonzero_exit(self):
        task_id = "fail-task"
        with patch(
            "app.backend.services.spotdl_service.get_playlist_info",
            return_value={"name": "Test", "track_count": 10},
        ), patch(
            "app.backend.services.spotdl_service.create_download_task"
        ), patch(
            "app.backend.services.spotdl_service.update_download_task"
        ) as mock_update, patch(
            "asyncio.create_subprocess_exec", new_callable=AsyncMock
        ) as mock_subprocess:
            mock_proc = MagicMock()
            mock_proc.pid = 12345
            # Simulate some output then EOF to avoid infinite loop in _read_stream
            mock_proc.stdout.read = AsyncMock(side_effect=[b"Error\n", b""])
            mock_proc.wait = AsyncMock(return_value=1)  # non-zero
            mock_subprocess.return_value = mock_proc

            asyncio.run(download_playlist("pl", "/tmp", task_id, auto_organize=False))

            # Check final status is failed
            statuses = [args[1].get("status") for args, kwargs in mock_update.call_args_list if len(args) >= 2 and "status" in args[1]]
            assert "failed" in statuses

    def test_cancel_download(self):
        """Test cancellation of a running download."""
        task_id = "cancel-task"
        clear_running_processes()  # ensure clean state

        # We'll manually insert a fake process into the global registry to test cancel logic
        # Because cancel_download looks up _running_processes[task_id]
        mock_proc = MagicMock()
        mock_proc.pid = 9999
        mock_proc.terminate = MagicMock()  # terminate is synchronous
        mock_proc.wait = AsyncMock(return_value=0)  # wait is async, returns exit code

        # Insert into registry manually
        _running_processes[task_id] = mock_proc

        # Also need to patch update_download_task
        with patch("app.backend.services.spotdl_service.update_download_task") as mock_update:
            # cancel_download is async, so run it
            result = asyncio.run(cancel_download(task_id))
            assert result is True
            mock_proc.terminate.assert_called_once()
            # Check update called with cancelled status
            update_call = mock_update.call_args[1] if mock_update.call_args[1] else mock_update.call_args[0][1]
            assert update_call.get("status") == "cancelled"
            assert task_id not in _running_processes

    def test_cancel_download_not_running(self):
        clear_running_processes()
        with patch("app.backend.services.spotdl_service.update_download_task") as mock_update:
            result = asyncio.run(cancel_download("missing"))
            assert result is False
            mock_update.assert_not_called()


class TestGetDownloadStatus:
    """Tests for get_download_status function."""

    @patch("app.backend.services.spotdl_service.get_download_task")
    @patch("app.backend.services.spotdl_service.get_progress_history")
    def test_returns_status_dict(self, mock_history, mock_task):
        mock_task.return_value = {
            "task_id": "t1",
            "status": "downloading",
            "playlist_id": "pl1",
            "playlist_name": "Test",
            "destination": "/tmp",
            "total_tracks": 10,
            "completed_tracks": 5,
            "progress_percent": 50.0,
            "current_track": "Track 5",
            "auto_organize": True,
            "spotdl_pid": 123,
            "error_message": None,
            "started_at": 1000,
            "finished_at": None,
        }
        mock_history.return_value = [
            {"timestamp": 1, "percent": 10.0, "current_track": "T1", "completed_tracks": 1, "total_tracks": 10},
            {"timestamp": 2, "percent": 50.0, "current_track": "T5", "completed_tracks": 5, "total_tracks": 10},
        ]

        status = get_download_status("t1")
        assert status is not None
        assert status["task_id"] == "t1"
        assert status["status"] == "downloading"
        assert status["progress_percent"] == 50.0
        assert len(status["progress_history"]) == 2

    @patch("app.backend.services.spotdl_service.get_download_task")
    def test_returns_none_if_not_found(self, mock_task):
        mock_task.return_value = None
        assert get_download_status("missing") is None
