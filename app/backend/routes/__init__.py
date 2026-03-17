"""
API route handlers.
"""

import logging
import requests
from typing import Optional
from fastapi import APIRouter, HTTPException, Body
from ..services import analyze_service, organize_service, auth_service, spotify_service
from ..models import (
    AnalyzeRequest,
    OrganizeRequest,
    AnalyzeResult,
    OrganizeResult,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["api"])


@router.post("/analyze", response_model=AnalyzeResult)
async def analyze_endpoint(request: AnalyzeRequest):
    """
    Analyze a music library and return genre distribution statistics.
    """
    try:
        result = analyze_service(
            source=request.source,
            level=request.level,
            limit=request.limit,
            exclude_dir=request.exclude_dir,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.post("/organize", response_model=OrganizeResult)
async def organize_endpoint(request: OrganizeRequest):
    """
    Organize files into genre-based folder structure.
    """
    try:
        result = organize_service(
            source=request.source,
            destination=request.destination,
            mode=request.mode,
            level=request.level,
            profile=request.profile,
            dry_run=request.dry_run,
            skip_existing=request.skip_existing,
            skip_unknown_only=request.skip_unknown_only,
            on_collision=request.on_collision,
            limit=request.limit,
            exclude_dir=request.exclude_dir,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Organization failed: {str(e)}")


# --- Spotify Auth Routes ---

from ..models import SpotifyPlaylist


@router.get("/auth/spotify/login")
async def spotify_login():
    """
    Initiates Spotify OAuth flow.

    Returns:
        Redirect to Spotify authorization page.
    """
    try:
        verifier, challenge = auth_service.generate_pkce_pair()
        # Store verifier in temporary in-memory store (or session if web)
        # For desktop app, we'll store it in a simple global cache keyed by random state
        import uuid
        state = str(uuid.uuid4())
        # TODO: persist verifier with state in a short-lived store (e.g., file or memory)
        # For now, return both URL and state; desktop app must redirect user and later present state+code+verifier to callback
        url = auth_service.get_auth_url(verifier, state=state)
        return {"auth_url": url, "state": state, "code_verifier": verifier}
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/auth/spotify/callback")
async def spotify_callback(code: str, state: Optional[str] = None):
    """
    OAuth callback endpoint (GET). Spotify redirects here with authorization code.

    Args:
        code: Authorization code from Spotify
        state: State parameter for CSRF validation (optional)

    Note:
        This GET endpoint returns an error directing clients to use POST,
        because code_verifier must be sent in body for security. Desktop apps
        should intercept the callback URL and instead call POST /auth/spotify/callback
        directly with the code and the stored code_verifier.
    """
    raise HTTPException(
        status_code=400,
        detail="Use POST /auth/spotify/callback with code_verifier in request body",
    )


@router.post("/auth/spotify/callback")
async def spotify_callback_post(
    code: str = Body(..., embed=True), code_verifier: str = Body(..., embed=True)
):
    """
    OAuth callback (POST). Exchange code for tokens.

    Args:
        code: Authorization code from Spotify
        code_verifier: Original PKCE code verifier generated during /login

    Returns:
        Success status and basic user info (if available)
    """
    try:
        tokens = auth_service.exchange_code_for_tokens(code, code_verifier)
        return {"success": True, "access_token": tokens.access_token}
    except requests.HTTPError as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Token exchange failed: {e.response.text if e.response else e}")
        raise HTTPException(status_code=400, detail="Invalid authorization code")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Authentication failed: {str(e)}")


@router.get("/auth/spotify/status")
async def spotify_status():
    """
    Check current Spotify authentication status.

    Returns:
        {"connected": bool, "username": str?}
        If token is expired, attempts transparent refresh.
    """
    try:
        tokens = auth_service.load_oauth()
        if not tokens:
            return {"connected": False}

        if auth_service.is_token_expired(tokens.expires_at):
            logger = logging.getLogger(__name__)
            logger.info("Token expired; attempting refresh")
            try:
                tokens = auth_service.refresh_access_token(tokens.refresh_token)
            except Exception as e:
                logger.error(f"Refresh failed: {e}")
                # Token likely invalid; treat as disconnected
                return {"connected": False}

        # We could fetch the actual Spotify user profile here to get username
        # For MVP, just return connected=True (username requires extra API call)
        return {"connected": True}
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Status check failed: {e}")
        return {"connected": False}


# --- Spotify Playlist Routes ---

@router.get("/spotify/playlists")
async def spotify_playlists(limit: int = 50):
    """
    List user's Spotify playlists.
    Requires Spotify authentication.

    Args:
        limit: Maximum number of playlists to return (max 50)

    Returns:
        {"playlists": [SpotifyPlaylist, ...]}
    """
    try:
        playlists = spotify_service.get_available_playlists(limit=limit)
        return {"playlists": [p.model_dump() for p in playlists]}
    except RuntimeError as e:
        # Not authenticated
        raise HTTPException(status_code=401, detail=str(e))
    except requests.HTTPError as e:
        if e.response is not None:
            if e.response.status_code == 401:
                raise HTTPException(status_code=401, detail="Not authenticated or token expired")
            elif e.response.status_code == 429:
                raise HTTPException(status_code=429, detail="Spotify API rate limit exceeded")
        raise HTTPException(status_code=500, detail=f"Spotify API error: {e}")
    except Exception as e:
        logger.exception("Failed to fetch playlists")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/spotify/playlist/{playlist_id}/tracks")
async def spotify_playlist_tracks(
    playlist_id: str,
    limit: int = 100,
    offset: int = 0,
):
    """
    Get tracks from a specific playlist.

    Args:
        playlist_id: Spotify playlist ID
        limit: Maximum number of tracks to return (max 100)
        offset: Pagination offset

    Returns:
        {"tracks": [SpotifyTrack, ...], "total": int}
    """
    try:
        tracks = spotify_service.get_playlist_tracks(
            playlist_id=playlist_id,
            limit=limit,
            offset=offset,
        )
        return {"tracks": [t.model_dump() for t in tracks], "total": len(tracks)}
    except RuntimeError as e:
        # Not authenticated
        raise HTTPException(status_code=401, detail=str(e))
    except requests.HTTPError as e:
        if e.response is not None:
            if e.response.status_code in (401, 403):
                raise HTTPException(status_code=e.response.status_code, detail="Access denied")
            elif e.response.status_code == 404:
                raise HTTPException(status_code=404, detail="Playlist not found")
            elif e.response.status_code == 429:
                raise HTTPException(status_code=429, detail="Spotify API rate limit exceeded")
        raise HTTPException(status_code=500, detail=f"Spotify API error: {e}")
    except Exception as e:
        logger.exception(f"Failed to fetch tracks for playlist {playlist_id}")
        raise HTTPException(status_code=500, detail=str(e))
