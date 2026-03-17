"""
Tests for Spotify service layer.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import requests

from app.backend.services.spotify_service import (
    get_available_playlists,
    get_playlist_tracks,
)
from app.backend.models import SpotifyPlaylist, SpotifyTrack


class TestGetAvailablePlaylists:
    """Tests for fetching user playlists."""

    @patch("app.backend.services.spotify_service.requests.get")
    @patch("app.backend.services.spotify_service.auth_service.get_valid_access_token")
    def test_returns_list_of_playlists(self, mock_token, mock_get):
        mock_token.return_value = "test_token"
        mock_response = Mock()
        mock_response.json.return_value = {
            "items": [
                {
                    "id": "playlist_1",
                    "name": "Chill Vibes",
                    "owner": {"display_name": "dj_user"},
                    "tracks": {"total": 50},
                    "snapshot_id": "abc123",
                },
                {
                    "id": "playlist_2",
                    "name": "Workout Mix",
                    "owner": {"display_name": "another_user"},
                    "tracks": {"total": 25},
                    "snapshot_id": None,
                },
            ],
            "total": 2,
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        playlists = get_available_playlists(limit=50)

        assert len(playlists) == 2
        assert isinstance(playlists[0], SpotifyPlaylist)
        assert playlists[0].id == "playlist_1"
        assert playlists[0].name == "Chill Vibes"
        assert playlists[0].owner == "dj_user"
        assert playlists[0].track_count == 50
        assert playlists[1].snapshot_id is None

    @patch("app.backend.services.spotify_service.auth_service.get_valid_access_token")
    def test_raises_runtime_error_if_not_authenticated(self, mock_token):
        mock_token.return_value = None
        with pytest.raises(RuntimeError, match="Not authenticated"):
            get_available_playlists()

    @patch("app.backend.services.spotify_service.requests.get")
    @patch("app.backend.services.spotify_service.auth_service.get_valid_access_token")
    def test_respects_limit_parameter(self, mock_token, mock_get):
        mock_token.return_value = "token"
        mock_response = Mock()
        mock_response.json.return_value = {"items": []}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        get_available_playlists(limit=25)
        # Verify request params contain limit=25
        _, kwargs = mock_get.call_args
        assert kwargs["params"]["limit"] == 25

    @patch("app.backend.services.spotify_service.requests.get")
    @patch("app.backend.services.spotify_service.auth_service.get_valid_access_token")
    def test_caps_limit_to_50(self, mock_token, mock_get):
        mock_token.return_value = "token"
        mock_response = Mock()
        mock_response.json.return_value = {"items": []}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        get_available_playlists(limit=100)  # Request 100
        # Should be capped to 50 in request params
        _, kwargs = mock_get.call_args
        assert kwargs["params"]["limit"] == 50

    @patch("app.backend.services.spotify_service.requests.get")
    @patch("app.backend.services.spotify_service.auth_service.get_valid_access_token")
    def test_handles_http_401_unauthorized(self, mock_token, mock_get):
        mock_token.return_value = "token"
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("401")
        mock_get.return_value = mock_response

        with pytest.raises(requests.HTTPError):
            get_available_playlists()

    @patch("app.backend.services.spotify_service.requests.get")
    @patch("app.backend.services.spotify_service.auth_service.get_valid_access_token")
    def test_handles_empty_items_list(self, mock_token, mock_get):
        mock_token.return_value = "token"
        mock_response = Mock()
        mock_response.json.return_value = {"items": []}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        playlists = get_available_playlists()
        assert playlists == []

    @patch("app.backend.services.spotify_service.requests.get")
    @patch("app.backend.services.spotify_service.auth_service.get_valid_access_token")
    def test_handles_missing_optional_fields_gracefully(self, mock_token, mock_get):
        mock_token.return_value = "token"
        mock_response = Mock()
        mock_response.json.return_value = {
            "items": [
                {
                    "id": "pl1",
                    "name": "Minimal",
                    # owner missing
                    # tracks missing
                    # snapshot_id missing
                }
            ]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        playlists = get_available_playlists()
        assert playlists[0].owner == "Unknown"
        assert playlists[0].track_count == 0
        assert playlists[0].snapshot_id is None


class TestGetPlaylistTracks:
    """Tests for fetching playlist tracks."""

    @patch("app.backend.services.spotify_service.requests.get")
    @patch("app.backend.services.spotify_service.auth_service.get_valid_access_token")
    def test_returns_list_of_tracks(self, mock_token, mock_get):
        mock_token.return_value = "token"
        mock_response = Mock()
        mock_response.json.return_value = {
            "items": [
                {
                    "track": {
                        "id": "track1",
                        "name": "Song One",
                        "artists": [{"name": "Artist A"}, {"name": "Artist B"}],
                        "album": {
                            "name": "Album X",
                            "duration_ms": 210000,
                        },
                        "track_number": 1,
                        "disc_number": 1,
                        "isrc": "US-123-456-789",
                        "external_urls": {"spotify": "https://open.spotify.com/track/1"},
                        "is_local": False,
                        "duration_ms": 180000,
                    }
                }
            ],
            "total": 1,
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        tracks = get_playlist_tracks("playlist_123")

        assert len(tracks) == 1
        track = tracks[0]
        assert isinstance(track, SpotifyTrack)
        assert track.id == "track1"
        assert track.name == "Song One"
        assert track.artist == "Artist A, Artist B"
        assert track.album == "Album X"
        assert track.duration_ms == 180000
        assert track.track_number == 1
        assert track.disc_number == 1
        assert track.isrc == "US-123-456-789"

    @patch("app.backend.services.spotify_service.auth_service.get_valid_access_token")
    def test_raises_runtime_error_if_not_authenticated(self, mock_token):
        mock_token.return_value = None
        with pytest.raises(RuntimeError, match="Not authenticated"):
            get_playlist_tracks("pl123")

    @patch("app.backend.services.spotify_service.requests.get")
    @patch("app.backend.services.spotify_service.auth_service.get_valid_access_token")
    def test_handles_missing_track_data(self, mock_token, mock_get):
        mock_token.return_value = "token"
        mock_response = Mock()
        mock_response.json.return_value = {
            "items": [
                {"track": None},  # Missing track
                {"track": {"id": "t2", "name": "Valid", "artists": [], "album": {}}},
            ]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        tracks = get_playlist_tracks("pl")
        assert len(tracks) == 1
        assert tracks[0].name == "Valid"
        assert tracks[0].artist == "Unknown"  # empty artists list

    @patch("app.backend.services.spotify_service.requests.get")
    @patch("app.backend.services.spotify_service.auth_service.get_valid_access_token")
    def test_skips_local_tracks_but_still_includes(self, mock_token, mock_get):
        """Local tracks may have minimal data; test that they're still returned."""
        mock_token.return_value = "token"
        mock_response = Mock()
        mock_response.json.return_value = {
            "items": [
                {
                    "track": {
                        "id": None,  # local tracks often have no ID
                        "name": "Local File",
                        "artists": [{"name": "Local Artist"}],
                        "album": {"name": "Local Album"},
                        "is_local": True,
                    }
                }
            ]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        tracks = get_playlist_tracks("pl")
        assert len(tracks) == 1
        assert tracks[0].name == "Local File"
        assert tracks[0].id is None or tracks[0].id == ""  # may be empty

    @patch("app.backend.services.spotify_service.requests.get")
    @patch("app.backend.services.spotify_service.auth_service.get_valid_access_token")
    def test_caps_limit_to_100(self, mock_token, mock_get):
        mock_token.return_value = "token"
        mock_response = Mock()
        mock_response.json.return_value = {"items": []}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        get_playlist_tracks("pl", limit=200)
        _, kwargs = mock_get.call_args
        assert kwargs["params"]["limit"] == 100

    @patch("app.backend.services.spotify_service.requests.get")
    @patch("app.backend.services.spotify_service.auth_service.get_valid_access_token")
    def test_handles_404_and_403_errors(self, mock_token, mock_get):
        mock_token.return_value = "token"
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("403")
        mock_get.return_value = mock_response

        with pytest.raises(requests.HTTPError):
            get_playlist_tracks("invalid_id")

    @patch("app.backend.services.spotify_service.requests.get")
    @patch("app.backend.services.spotify_service.auth_service.get_valid_access_token")
    def test_artist_join_with_many_artists(self, mock_token, mock_get):
        mock_token.return_value = "token"
        mock_response = Mock()
        mock_response.json.return_value = {
            "items": [
                {
                    "track": {
                        "id": "t1",
                        "name": "Collab",
                        "artists": [
                            {"name": "A"},
                            {"name": "B"},
                            {"name": "C"},
                        ],
                        "album": {},
                    }
                }
            ]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        tracks = get_playlist_tracks("pl")
        assert tracks[0].artist == "A, B, C"
