"""
Tests for download API routes.
"""

from unittest.mock import patch, AsyncMock, MagicMock
import pytest
from fastapi.testclient import TestClient
from app.backend.main import app

client = TestClient(app)


class TestStartDownload:
    """Tests for POST /downloads."""

    @patch("app.backend.routes.spotdl_service.download_playlist")
    @patch("app.backend.routes.spotify_service.get_playlist_info")
    @patch("app.backend.routes.create_download_task")
    @patch("app.backend.routes.auth_service.get_valid_access_token")
    def test_start_download_returns_task_id(
        self, mock_token, mock_create_task, mock_get_info, mock_download
    ):
        mock_token.return_value = "token"
        mock_get_info.return_value = {"name": "My Playlist", "track_count": 5}
        # create_download_task doesn't return anything
        mock_create_task.return_value = None
        # download_playlist is async but we don't await; should be called in background
        mock_download.return_value = None  # coroutine that does nothing

        response = client.post(
            "/api/v1/downloads",
            json={"playlist_id": "pl123", "destination": "/tmp/music", "auto_organize": True},
        )
        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        assert data["status"] == "queued"

        # Verify create_download_task was called with correct args
        assert mock_create_task.call_count == 1
        call_kwargs = mock_create_task.call_args[1]
        assert call_kwargs["playlist_id"] == "pl123"
        assert call_kwargs["destination"] == "/tmp/music"
        assert call_kwargs["auto_organize"] is True

    @patch("app.backend.routes.auth_service.get_valid_access_token")
    def test_start_download_requires_auth(self, mock_token):
        mock_token.return_value = None
        response = client.post(
            "/api/v1/downloads",
            json={"playlist_id": "pl123", "destination": "/tmp"},
        )
        assert response.status_code == 401

    def test_missing_required_fields_returns_422(self):
        response = client.post("/api/v1/downloads", json={})
        assert response.status_code == 422  # Unprocessable Entity


class TestGetDownloadStatus:
    """Tests for GET /downloads/{task_id}/status."""

    @patch("app.backend.routes.spotdl_service.get_download_status")
    def test_returns_status_when_found(self, mock_status):
        mock_status.return_value = {
            "task_id": "t1",
            "status": "downloading",
            "progress_percent": 50.0,
            "current_track": "Track 5",
            "total_tracks": 10,
            "completed_tracks": 5,
            "playlist_name": "Test",
            "destination": "/tmp",
            "auto_organize": True,
            "spotdl_pid": 123,
            "error_message": None,
            "started_at": 1000,
            "finished_at": None,
            "progress_history": [],
        }
        response = client.get("/api/v1/downloads/t1/status")
        assert response.status_code == 200
        assert response.json()["task_id"] == "t1"

    @patch("app.backend.routes.spotdl_service.get_download_status")
    def test_returns_404_when_not_found(self, mock_status):
        mock_status.return_value = None
        response = client.get("/api/v1/downloads/unknown/status")
        assert response.status_code == 404


class TestCancelDownload:
    """Tests for POST /downloads/{task_id}/cancel."""

    @patch("app.backend.routes.spotdl_service.cancel_download")
    def test_cancel_returns_true(self, mock_cancel):
        mock_cancel.return_value = True
        response = client.post("/api/v1/downloads/t1/cancel")
        assert response.status_code == 200
        assert response.json()["cancelled"] is True

    @patch("app.backend.routes.spotdl_service.cancel_download")
    def test_cancel_returns_false_if_not_running(self, mock_cancel):
        mock_cancel.return_value = False
        response = client.post("/api/v1/downloads/t1/cancel")
        assert response.status_code == 200
        assert response.json()["cancelled"] is False
