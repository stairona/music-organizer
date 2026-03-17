"""
Spotify authentication service using OAuth 2.0 PKCE.
No client secret required — suitable for desktop apps.
"""

import base64
import hashlib
import logging
import os
import secrets
import webbrowser
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, Tuple

import requests
from urllib.parse import urlencode

from ..store import get_oauth_tokens, save_oauth_tokens, delete_oauth_tokens
from ..models import OAuthTokens

logger = logging.getLogger(__name__)

# Spotify OAuth endpoints
SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"

# Required env var
CLIENT_ID = os.environ.get("SPOTIPY_CLIENT_ID")
if not CLIENT_ID:
    logger.warning("SPOTIPY_CLIENT_ID not set; Spotify auth will fail")


def generate_pkce_pair() -> Tuple[str, str]:
    """
    Generate PKCE code verifier and challenge.

    Returns:
        (code_verifier, code_challenge) tuple
    """
    # Verifier: 32-96 chars, URL-safe random string
    code_verifier = secrets.token_urlsafe(64)[:64]
    # Challenge: base64url-encoded SHA256 hash of verifier
    digest = hashlib.sha256(code_verifier.encode("utf-8")).digest()
    code_challenge = base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")
    return code_verifier, code_challenge


def get_auth_url(code_verifier: str, state: Optional[str] = None) -> str:
    """
    Build Spotify OAuth authorization URL with PKCE.

    Args:
        code_verifier: PKCE code verifier (will be verified by callback)
        state: Optional state parameter for CSRF protection

    Returns:
        Full authorization URL (user should visit or open in browser)
    """
    if not CLIENT_ID:
        raise ValueError("SPOTIPY_CLIENT_ID environment variable not set")

    _, code_challenge = generate_pkce_pair_from_verifier(code_verifier)
    params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": "http://localhost:8080/callback",  # Desktop app callback
        "code_challenge_method": "S256",
        "code_challenge": code_challenge,
        "scope": "playlist-read-private playlist-read-collaborative",
    }
    if state:
        params["state"] = state

    query = urlencode(params)
    return f"{SPOTIFY_AUTH_URL}?{query}"


def generate_pkce_pair_from_verifier(code_verifier: str) -> Tuple[str, str]:
    """Helper: compute challenge from existing verifier."""
    digest = hashlib.sha256(code_verifier.encode("utf-8")).digest()
    code_challenge = base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")
    return code_verifier, code_challenge


def exchange_code_for_tokens(
    auth_code: str,
    code_verifier: str,
    redirect_uri: str = "http://localhost:8080/callback",
) -> OAuthTokens:
    """
    Exchange authorization code for access/refresh tokens.

    Args:
        auth_code: Authorization code from Spotify callback
        code_verifier: Original PKCE code verifier
        redirect_uri: Must match the one used in auth_url

    Returns:
        OAuthTokens with access_token, refresh_token, expires_at

    Raises:
        requests.HTTPError on failure
    """
    if not CLIENT_ID:
        raise ValueError("SPOTIPY_CLIENT_ID environment variable not set")

    data = {
        "client_id": CLIENT_ID,
        "grant_type": "authorization_code",
        "code": auth_code,
        "redirect_uri": redirect_uri,
        "code_verifier": code_verifier,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    response = requests.post(SPOTIFY_TOKEN_URL, data=data, headers=headers, timeout=10)
    response.raise_for_status()
    token_data = response.json()

    access_token = token_data["access_token"]
    refresh_token = token_data["refresh_token"]
    expires_in = token_data["expires_in"]  # seconds

    # Compute absolute expiry timestamp (with 5% safety buffer)
    now = datetime.now(timezone.utc)
    expires_at = int((now + timedelta(seconds=int(expires_in * 0.95))).timestamp())

    tokens = OAuthTokens(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_at=expires_at,
    )
    # Auto-store after successful exchange
    store_oauth(tokens)
    return tokens


def refresh_access_token(refresh_token: str) -> OAuthTokens:
    """
    Use refresh token to obtain new access token.

    Args:
        refresh_token: Valid refresh token

    Returns:
        New OAuthTokens (with new access_token and new expires_at)

    Raises:
        requests.HTTPError if refresh fails (e.g., refresh token revoked)
    """
    if not CLIENT_ID:
        raise ValueError("SPOTIPY_CLIENT_ID environment variable not set")

    data = {
        "client_id": CLIENT_ID,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    response = requests.post(SPOTIFY_TOKEN_URL, data=data, headers=headers, timeout=10)
    response.raise_for_status()
    token_data = response.json()

    access_token = token_data["access_token"]
    # Spotify may not return new refresh_token; keep existing if missing
    new_refresh_token = token_data.get("refresh_token", refresh_token)
    expires_in = token_data["expires_in"]

    now = datetime.now(timezone.utc)
    expires_at = int((now + timedelta(seconds=int(expires_in * 0.95))).timestamp())

    tokens = OAuthTokens(
        access_token=access_token,
        refresh_token=new_refresh_token,
        expires_at=expires_at,
    )
    store_oauth(tokens)
    return tokens


def load_oauth() -> Optional[OAuthTokens]:
    """
    Load stored OAuth tokens from persistent storage.

    Returns:
        OAuthTokens if present, None if not authenticated
    """
    tokens_dict = get_oauth_tokens()
    if tokens_dict:
        return OAuthTokens(
            access_token=tokens_dict["access_token"],
            refresh_token=tokens_dict["refresh_token"],
            expires_at=tokens_dict["expires_at"],
        )
    return None


def store_oauth(tokens: OAuthTokens) -> None:
    """
    Store OAuth tokens to persistent storage.

    Args:
        tokens: OAuthTokens to save
    """
    save_oauth_tokens(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        expires_at=tokens.expires_at,
    )


def is_token_expired(expires_at: int, buffer_seconds: int = 300) -> bool:
    """
    Check if token is expired or will expire within buffer.

    Args:
        expires_at: Unix timestamp
        buffer_seconds: Early expiry threshold (default 5 min)

    Returns:
        True if token is expired or within buffer window
    """
    now_ts = int(datetime.now(timezone.utc).timestamp())
    return now_ts >= (expires_at - buffer_seconds)


def get_valid_access_token() -> Optional[str]:
    """
    Get a valid access token, refreshing if needed and stored.
    Convenience function for API calls.

    Returns:
        access_token string, or None if not authenticated or refresh fails
    """
    tokens = load_oauth()
    if not tokens:
        return None

    if is_token_expired(tokens.expires_at):
        logger.info("Access token expired; refreshing...")
        try:
            tokens = refresh_access_token(tokens.refresh_token)
            return tokens.access_token
        except Exception as e:
            logger.error(f"Token refresh failed: {e}")
            return None

    return tokens.access_token


def logout() -> None:
    """Delete stored OAuth tokens (user logout)."""
    delete_oauth_tokens()
