"""
Tests for Spotify auth routes.
"""

import logging
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, Mock
import pytest
from fastapi.testclient import TestClient
from app.backend.main import app

client = TestClient(app)


class TestSpotifyLogin:
    """Tests for GET /auth/spotify/login."""

    @patch("app.backend.routes.auth_service.CLIENT_ID", "test_client")
    def test_returns_auth_url_and_state(self):
        response = client.get("/api/v1/auth/spotify/login")
        assert response.status_code == 200
        data = response.json()
        assert "auth_url" in data
        assert "state" in data
        assert "code_verifier" in data
        assert "accounts.spotify.com/authorize" in data["auth_url"]
        assert data["auth_url"].startswith("https://")

    @patch("app.backend.routes.auth_service.CLIENT_ID", None)
    def test_error_if_client_id_missing(self):
        response = client.get("/api/v1/auth/spotify/login")
        assert response.status_code == 500
        assert "SPOTIPY_CLIENT_ID" in response.json()["detail"]


class TestSpotifyCallbackGet:
    """Tests for GET /auth/spotify/callback (should direct to POST)."""

    def test_returns_error_instruction(self):
        response = client.get("/api/v1/auth/spotify/callback?code=123")
        assert response.status_code == 400
        assert "POST" in response.json()["detail"]


class TestSpotifyCallbackPost:
    """Tests for POST /auth/spotify/callback."""

    @patch("app.backend.routes.auth_service.exchange_code_for_tokens")
    def test_success(self, mock_exchange):
        from app.backend.models import OAuthTokens
        mock_tokens = OAuthTokens(
            access_token="new_access",
            refresh_token="new_refresh",
            expires_at=1700000000,
        )
        mock_exchange.return_value = mock_tokens

        response = client.post(
            "/api/v1/auth/spotify/callback",
            json={"code": "auth_code_123", "code_verifier": "verifier_abc"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["access_token"] == "new_access"
        mock_exchange.assert_called_once_with("auth_code_123", "verifier_abc")

    @patch("app.backend.routes.auth_service.exchange_code_for_tokens")
    def test_http_error_returns_400(self, mock_exchange):
        import requests
        mock_exchange.side_effect = requests.HTTPError("401")
        response = client.post(
            "/api/v1/auth/spotify/callback",
            json={"code": "bad_code", "code_verifier": "v"},
        )
        assert response.status_code == 400
        assert "Invalid authorization code" in response.json()["detail"]

    def test_missing_fields_returns_422(self):
        response = client.post("/api/v1/auth/spotify/callback", json={})
        assert response.status_code == 422  # Validation error


class TestSpotifyStatus:
    """Tests for GET /auth/spotify/status."""

    @patch("app.backend.routes.auth_service.load_oauth")
    def test_not_connected_when_no_tokens(self, mock_load):
        mock_load.return_value = None
        response = client.get("/api/v1/auth/spotify/status")
        assert response.status_code == 200
        assert response.json() == {"connected": False}

    @patch("app.backend.routes.auth_service.load_oauth")
    @patch("app.backend.routes.auth_service.is_token_expired")
    def test_connected_when_valid_tokens(self, mock_expired, mock_load):
        from app.backend.models import OAuthTokens
        tokens = OAuthTokens(
            access_token="valid",
            refresh_token="r",
            expires_at=int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()),
        )
        mock_load.return_value = tokens
        mock_expired.return_value = False

        response = client.get("/api/v1/auth/spotify/status")
        assert response.status_code == 200
        assert response.json()["connected"] is True

    @patch("app.backend.routes.auth_service.load_oauth")
    @patch("app.backend.routes.auth_service.is_token_expired")
    @patch("app.backend.routes.auth_service.refresh_access_token")
    def test_refresh_and_return_connected_if_success(self, mock_refresh, mock_expired, mock_load):
        from app.backend.models import OAuthTokens
        expired = OAuthTokens(
            access_token="expired",
            refresh_token="r",
            expires_at=int((datetime.now(timezone.utc) - timedelta(hours=1)).timestamp()),
        )
        mock_load.return_value = expired
        mock_expired.return_value = True
        refreshed = OAuthTokens(
            access_token="refreshed",
            refresh_token="r",
            expires_at=int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()),
        )
        mock_refresh.return_value = refreshed

        response = client.get("/api/v1/auth/spotify/status")
        assert response.status_code == 200
        assert response.json()["connected"] is True
        mock_refresh.assert_called_once_with("r")

    @patch("app.backend.routes.auth_service.load_oauth")
    @patch("app.backend.routes.auth_service.is_token_expired")
    @patch("app.backend.routes.auth_service.refresh_access_token")
    def test_returns_disconnected_if_refresh_fails(self, mock_refresh, mock_expired, mock_load):
        from app.backend.models import OAuthTokens
        expired = OAuthTokens(
            access_token="expired",
            refresh_token="r",
            expires_at=int((datetime.now(timezone.utc) - timedelta(hours=1)).timestamp()),
        )
        mock_load.return_value = expired
        mock_expired.return_value = True
        mock_refresh.side_effect = Exception("Refresh error")

        response = client.get("/api/v1/auth/spotify/status")
        assert response.status_code == 200
        assert response.json()["connected"] is False
