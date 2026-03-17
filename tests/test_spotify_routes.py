"""
Tests for Spotify playlist API routes.
"""

from unittest.mock import patch, Mock
import pytest
from fastapi.testclient import TestClient
from app.backend.main import app

client = TestClient(app)


class TestSpotifyPlaylists:
    """Tests for GET /spotify/playlists."""

    @patch("app.backend.routes.spotify_service.get_available_playlists")
    def test_success_returns_playlist_list(self, mock_get_playlists):
        from app.backend.models import SpotifyPlaylist

        mock_playlists = [
            SpotifyPlaylist(
                id="pl1", name="My Playlist", owner="user", track_count=42
            ),
            SpotifyPlaylist(
                id="pl2", name="Another", owner="user2", track_count=100
            ),
        ]
        mock_get_playlists.return_value = mock_playlists

        response = client.get("/api/v1/spotify/playlists")
        assert response.status_code == 200
        data = response.json()
        assert "playlists" in data
        assert len(data["playlists"]) == 2
        assert data["playlists"][0]["name"] == "My Playlist"
        assert data["playlists"][1]["track_count"] == 100

    @patch("app.backend.routes.spotify_service.get_available_playlists")
    def test_error_returns_500(self, mock_get_playlists):
        mock_get_playlists.side_effect = Exception("API error")
        response = client.get("/api/v1/spotify/playlists")
        assert response.status_code == 500
        assert "error" in response.json()["detail"].lower()

    @patch("app.backend.routes.spotify_service.get_available_playlists")
    def test_empty_list_returns_success(self, mock_get_playlists):
        mock_get_playlists.return_value = []
        response = client.get("/api/v1/spotify/playlists")
        assert response.status_code == 200
        assert response.json()["playlists"] == []


class TestSpotifyPlaylistTracks:
    """Tests for GET /spotify/playlist/{playlist_id}/tracks."""

    @patch("app.backend.routes.spotify_service.get_playlist_tracks")
    def test_success_returns_track_list(self, mock_get_tracks):
        from app.backend.models import SpotifyTrack

        mock_tracks = [
            SpotifyTrack(
                id="t1",
                name="Track 1",
                artist="Artist X",
                album="Album A",
                duration_ms=180000,
            ),
            SpotifyTrack(
                id="t2",
                name="Track 2",
                artist="Artist Y",
                album="Album B",
                duration_ms=200000,
            ),
        ]
        mock_get_tracks.return_value = mock_tracks

        response = client.get("/api/v1/spotify/playlist/pl123/tracks")
        assert response.status_code == 200
        data = response.json()
        assert "tracks" in data
        assert len(data["tracks"]) == 2
        assert data["tracks"][0]["name"] == "Track 1"
        assert "total" in data

    @patch("app.backend.routes.spotify_service.get_playlist_tracks")
    def test_404_playlist_not_found(self, mock_get_tracks):
        import requests
        from unittest.mock import Mock

        mock_resp = Mock()
        mock_resp.status_code = 404
        mock_get_tracks.side_effect = requests.HTTPError("404", response=mock_resp)
        response = client.get("/api/v1/spotify/playlist/nonexistent/tracks")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @patch("app.backend.routes.spotify_service.get_playlist_tracks")
    def test_403_access_denied(self, mock_get_tracks):
        import requests
        from unittest.mock import Mock

        mock_resp = Mock()
        mock_resp.status_code = 403
        mock_get_tracks.side_effect = requests.HTTPError("403", response=mock_resp)
        response = client.get("/api/v1/spotify/playlist/pl/tracks")
        assert response.status_code == 403
        assert "access denied" in response.json()["detail"].lower()

    @patch("app.backend.routes.spotify_service.get_playlist_tracks")
    def test_error_returns_500(self, mock_get_tracks):
        mock_get_tracks.side_effect = Exception("Unexpected error")
        response = client.get("/api/v1/spotify/playlist/pl/tracks")
        assert response.status_code == 500

    def test_invalid_playlist_id_allows_request(self):
        # No validation on playlist_id string; should pass through
        response = client.get("/api/v1/spotify/playlist/123/tracks")
        # Will fail auth (401) but not validation
        assert response.status_code in (401, 500)
