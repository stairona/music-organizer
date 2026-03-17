"""
Tests for Spotify auth_service.
"""

import base64
import hashlib
import logging
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch
import pytest
import requests

from app.backend.services.auth_service import (
    generate_pkce_pair,
    get_auth_url,
    exchange_code_for_tokens,
    refresh_access_token,
    load_oauth,
    store_oauth,
    is_token_expired,
    get_valid_access_token,
    logout,
    generate_pkce_pair_from_verifier,
    CLIENT_ID,
)
from app.backend.models import OAuthTokens


class TestPKCE:
    """Tests for PKCE pair generation."""

    def test_generate_pkce_pair_returns_two_strings(self):
        verifier, challenge = generate_pkce_pair()
        assert isinstance(verifier, str)
        assert isinstance(challenge, str)
        assert len(verifier) >= 32
        assert len(verifier) <= 64
        assert "/" not in verifier  # URL-safe
        assert "+" not in verifier

    def test_challenge_is_base64_url_safe_sha256_of_verifier(self):
        verifier = "test_verifier_123"
        verifier_out, challenge = generate_pkce_pair_from_verifier(verifier)
        assert verifier_out == verifier
        # Compute expected challenge
        expected_digest = hashlib.sha256(verifier.encode()).digest()
        expected_challenge = base64.urlsafe_b64encode(expected_digest).decode().rstrip("=")
        assert challenge == expected_challenge


class TestGetAuthUrl:
    """Tests for auth URL construction."""

    @patch("app.backend.services.auth_service.CLIENT_ID", "test_client_id")
    def test_builds_correct_url(self):
        verifier = "test_verifier"
        url = get_auth_url(verifier, state="abc123")
        assert "accounts.spotify.com/authorize" in url
        assert "client_id=test_client_id" in url
        assert "response_type=code" in url
        assert "code_challenge=" in url
        assert "code_challenge_method=S256" in url
        # Scope can be space-separated or plus-separated in URL encoding
        assert "playlist-read-private" in url and "playlist-read-collaborative" in url
        assert "state=abc123" in url
        assert "redirect_uri=http%3A%2F%2Flocalhost%3A8080%2Fcallback" in url

    @patch("app.backend.services.auth_service.CLIENT_ID", None)
    def test_raises_if_client_id_missing(self):
        with pytest.raises(ValueError, match="SPOTIPY_CLIENT_ID"):
            get_auth_url("verifier")


class TestExchangeCodeForTokens:
    """Tests for token exchange."""

    @patch("app.backend.services.auth_service.CLIENT_ID", "test_id")
    @patch("app.backend.services.auth_service.requests.post")
    @patch("app.backend.services.auth_service.store_oauth")
    def test_exchange_success(self, mock_store, mock_post):
        # Mock Spotify response
        mock_response = Mock()
        mock_response.json.return_value = {
            "access_token": "access_token_123",
            "refresh_token": "refresh_token_456",
            "expires_in": 3600,
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        tokens = exchange_code_for_tokens("auth_code", "verifier")

        assert tokens.access_token == "access_token_123"
        assert tokens.refresh_token == "refresh_token_456"
        assert isinstance(tokens.expires_at, int)
        # store_oauth called
        mock_store.assert_called_once()

    @patch("app.backend.services.auth_service.CLIENT_ID", None)
    def test_raises_if_client_id_missing(self):
        with pytest.raises(ValueError, match="SPOTIPY_CLIENT_ID"):
            exchange_code_for_tokens("code", "verifier")

    @patch("app.backend.services.auth_service.CLIENT_ID", "test_id")
    @patch("app.backend.services.auth_service.requests.post")
    def test_http_error_propagates(self, mock_post):
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("401")
        mock_post.return_value = mock_response

        with pytest.raises(requests.HTTPError):
            exchange_code_for_tokens("bad_code", "verifier")


class TestRefreshAccessToken:
    """Tests for token refresh."""

    @patch("app.backend.services.auth_service.CLIENT_ID", "test_id")
    @patch("app.backend.services.auth_service.requests.post")
    @patch("app.backend.services.auth_service.store_oauth")
    def test_refresh_success(self, mock_store, mock_post):
        mock_response = Mock()
        mock_response.json.return_value = {
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token",  # may or may not return refresh
            "expires_in": 3600,
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        tokens = refresh_access_token("old_refresh_token")

        assert tokens.access_token == "new_access_token"
        assert tokens.refresh_token == "new_refresh_token"
        mock_store.assert_called_once()

    @patch("app.backend.services.auth_service.CLIENT_ID", "test_id")
    @patch("app.backend.services.auth_service.requests.post")
    def test_refresh_keeps_old_refresh_if_not_returned(self, mock_post):
        mock_response = Mock()
        mock_response.json.return_value = {
            "access_token": "new_access_token",
            "expires_in": 3600,
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        tokens = refresh_access_token("old_refresh_token")
        assert tokens.refresh_token == "old_refresh_token"


class TestLoadStoreOAuth:
    """Tests for token persistence."""

    def test_store_and_load(self, tmp_path, monkeypatch):
        # Isolate store DB
        from app.backend.store import RUN_HISTORY_DIR
        temp_dir = tmp_path / "config"
        monkeypatch.setattr("app.backend.store.RUN_HISTORY_DIR", str(temp_dir))
        from app.backend.store import _init_spotify_db
        _init_spotify_db()

        tokens = OAuthTokens(
            access_token="a",
            refresh_token="r",
            expires_at=1700000000,
        )
        store_oauth(tokens)
        loaded = load_oauth()
        assert loaded is not None
        assert loaded.access_token == "a"
        assert loaded.refresh_token == "r"
        assert loaded.expires_at == 1700000000

    def test_load_when_empty_returns_none(self, tmp_path, monkeypatch):
        # Create a fresh DB file and point store to it
        temp_db = tmp_path / "spotify_test.db"
        monkeypatch.setattr("app.backend.store.SPOTIFY_DB_PATH", str(temp_db))
        # Initialize the new DB
        from app.backend.store import _init_spotify_db
        _init_spotify_db()

        assert load_oauth() is None


class TestIsTokenExpired:
    """Tests for expiry check."""

    def test_expired_returns_true(self):
        # expired 1 hour ago
        expired_ts = int((datetime.now(timezone.utc) - timedelta(hours=1)).timestamp())
        assert is_token_expired(expired_ts) is True

    def test_not_expired_returns_false(self):
        # expires in 1 hour
        future_ts = int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp())
        assert is_token_expired(future_ts) is False

    def test_within_buffer_returns_true(self):
        # expires in 2 minutes, buffer default 5 min => should be true
        soon_ts = int((datetime.now(timezone.utc) + timedelta(minutes=2)).timestamp())
        assert is_token_expired(soon_ts) is True


class TestGetValidAccessToken:
    """Tests for get_valid_access_token convenience."""

    @patch("app.backend.services.auth_service.load_oauth")
    def test_returns_token_if_valid(self, mock_load):
        tokens = OAuthTokens(
            access_token="valid_token",
            refresh_token="r",
            expires_at=int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()),
        )
        mock_load.return_value = tokens
        token = get_valid_access_token()
        assert token == "valid_token"

    @patch("app.backend.services.auth_service.load_oauth")
    def test_returns_none_if_not_authenticated(self, mock_load):
        mock_load.return_value = None
        assert get_valid_access_token() is None

    @patch("app.backend.services.auth_service.load_oauth")
    @patch("app.backend.services.auth_service.refresh_access_token")
    def test_refreshes_if_expired(self, mock_refresh, mock_load):
        expired_tokens = OAuthTokens(
            access_token="expired",
            refresh_token="r",
            expires_at=int((datetime.now(timezone.utc) - timedelta(hours=1)).timestamp()),
        )
        mock_load.return_value = expired_tokens
        refreshed = OAuthTokens(
            access_token="new_token",
            refresh_token="r",
            expires_at=int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()),
        )
        mock_refresh.return_value = refreshed

        token = get_valid_access_token()
        assert token == "new_token"
        mock_refresh.assert_called_once_with("r")

    @patch("app.backend.services.auth_service.load_oauth")
    @patch("app.backend.services.auth_service.refresh_access_token")
    def test_returns_none_if_refresh_fails(self, mock_refresh, mock_load):
        expired_tokens = OAuthTokens(
            access_token="expired",
            refresh_token="r",
            expires_at=int((datetime.now(timezone.utc) - timedelta(hours=1)).timestamp()),
        )
        mock_load.return_value = expired_tokens
        mock_refresh.side_effect = Exception("refresh failed")

        assert get_valid_access_token() is None


class TestLogout:
    """Tests for logout."""

    @patch("app.backend.services.auth_service.delete_oauth_tokens")
    def test_logout_calls_delete(self, mock_delete):
        logout()
        mock_delete.assert_called_once()
