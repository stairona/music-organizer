"""
Tests for Spotify data models (Pydantic).
"""

import pytest
from datetime import datetime, timezone
from app.backend.models import (
    OAuthTokens,
    SpotifyPlaylist,
    SpotifyTrack,
    DownloadTask,
    ProgressSnapshot,
)


class TestOAuthTokens:
    """Tests for OAuthTokens model."""

    def test_creation(self):
        tokens = OAuthTokens(
            access_token="abc123",
            refresh_token="def456",
            expires_at=1700000000,
        )
        assert tokens.access_token == "abc123"
        assert tokens.refresh_token == "def456"
        assert tokens.expires_at == 1700000000

    def test_missing_fields_raise_error(self):
        with pytest.raises(ValueError):
            OAuthTokens(access_token="only")


class TestSpotifyPlaylist:
    """Tests for SpotifyPlaylist model."""

    def test_creation_all_fields(self):
        playlist = SpotifyPlaylist(
            id="37i9dQZF1DXcBWIGoYBM5M",
            name="Chill Hits",
            owner="spotify",
            track_count=100,
            snapshot_id="MTgzMzM5N...",
        )
        assert playlist.id == "37i9dQZF1DXcBWIGoYBM5M"
        assert playlist.name == "Chill Hits"
        assert playlist.track_count == 100
        assert playlist.snapshot_id == "MTgzMzM5N..."

    def test_optional_snapshot_id_defaults_none(self):
        playlist = SpotifyPlaylist(
            id="123", name="Test", owner="user", track_count=50
        )
        assert playlist.snapshot_id is None

    def test_missing_required_fields(self):
        with pytest.raises(ValueError):
            SpotifyPlaylist(id="123", name="Test")  # missing owner, track_count


class TestSpotifyTrack:
    """Tests for SpotifyTrack model."""

    def test_creation_all_fields(self):
        track = SpotifyTrack(
            id="track123",
            name="Midnight City",
            artist="M83",
            album="Hurry Up, We're Dreaming",
            duration_ms=243000,
            track_number=5,
            disc_number=1,
            isrc="US-XXX-XX-XX",
            external_urls={"spotify": "https://open.spotify.com/track/123"},
        )
        assert track.duration_ms == 243000
        assert track.track_number == 5

    def test_optional_fields_default_to_none(self):
        track = SpotifyTrack(
            id="t1", name="Song", artist="Artist", album="Album", duration_ms=180000
        )
        assert track.track_number is None
        assert track.disc_number == 1  # default
        assert track.isrc is None
        assert track.external_urls is None

    def test_missing_required_fields(self):
        with pytest.raises(ValueError):
            SpotifyTrack(id="t1", name="Song")  # missing artist, album, duration_ms


class TestDownloadTask:
    """Tests for DownloadTask model."""

    def test_creation_required_fields(self):
        task = DownloadTask(
            task_id="task-uuid-123",
            playlist_id="playlist-456",
            playlist_name="My Playlist",
            destination="/tmp/music",
            status="queued",
            total_tracks=10,
        )
        assert task.task_id == "task-uuid-123"
        assert task.status == "queued"
        assert task.total_tracks == 10
        assert task.completed_tracks == 0
        assert task.auto_organize is True
        assert task.progress_percent == 0.0

    def test_optional_fields_override_defaults(self):
        task = DownloadTask(
            task_id="task2",
            playlist_id="pl2",
            playlist_name="Another",
            destination="/dest",
            status="downloading",
            total_tracks=20,
            completed_tracks=5,
            auto_organize=False,
            organize_run_id="run-999",
            error_message="Network error",
            spotdl_pid=12345,
            progress_percent=25.5,
            current_track="Track 5",
            created_at=1700000000,
            started_at=1700000100,
        )
        assert task.completed_tracks == 5
        assert task.auto_organize is False
        assert task.progress_percent == 25.5

    def test_invalid_status(self):
        with pytest.raises(ValueError):
            DownloadTask(
                task_id="x",
                playlist_id="y",
                playlist_name="z",
                destination="/d",
                status="invalid_status",  # type: ignore
                total_tracks=1,
            )


class TestProgressSnapshot:
    """Tests for ProgressSnapshot model."""

    def test_creation(self):
        snap = ProgressSnapshot(
            task_id="task-123",
            timestamp=1700000000,
            percent=50.0,
            current_track="Track 3",
            completed_tracks=5,
            total_tracks=10,
            errors=["timeout"],
        )
        assert snap.percent == 50.0
        assert snap.errors == ["timeout"]

    def test_errors_default_empty(self):
        snap = ProgressSnapshot(
            task_id="t",
            timestamp=1700000000,
            percent=0.0,
            current_track="",
            completed_tracks=0,
            total_tracks=1,
        )
        assert snap.errors == []
