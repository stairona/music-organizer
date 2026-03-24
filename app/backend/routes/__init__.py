"""
API route handlers.
"""

import asyncio
import logging
import requests
import uuid
from typing import Optional
from fastapi import APIRouter, HTTPException, Body
from ..services import analyze_service, organize_service, auth_service, spotify_service, spotdl_service
from ..store import (
    create_download_task,
    update_download_task,
    add_progress_snapshot,
    get_download_task,
    get_progress_history,
)
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


# --- Download Routes ---

from ..models import DownloadTask


@router.post("/downloads")
async def start_download(
    playlist_id: str = Body(..., embed=True),
    destination: str = Body(..., embed=True),
    auto_organize: bool = Body(True, embed=True),
):
    """
    Start downloading a Spotify playlist.

    Args:
        playlist_id: Spotify playlist ID
        destination: Local directory to save files
        auto_organize: Whether to auto-organize after download (default True)

    Returns:
        {"task_id": str, "status": "queued"}
    """
    try:
        # Validate Spotify authentication using already-imported auth_service module
        if not auth_service.get_valid_access_token():
            raise HTTPException(status_code=401, detail="Not authenticated with Spotify")

        # Create a unique task ID
        import uuid
        task_id = str(uuid.uuid4())

        # Get playlist info for name and total tracks
        try:
            info = spotify_service.get_playlist_info(playlist_id)
            playlist_name = info.get("name", "Unknown Playlist")
            total_tracks = info.get("track_count", 0)
        except Exception as e:
            logger.warning(f"Failed to fetch playlist info: {e}")
            playlist_name = "Unknown Playlist"
            total_tracks = 0

        # Create download task record
        create_download_task(
            task_id=task_id,
            playlist_id=playlist_id,
            playlist_name=playlist_name,
            destination=destination,
            total_tracks=total_tracks,
            auto_organize=auto_organize,
        )

        # Launch download in background (do not await)
        asyncio.create_task(
            spotdl_service.download_playlist(
                playlist_id=playlist_id,
                destination=destination,
                task_id=task_id,
                auto_organize=auto_organize,
            )
        )

        return {"task_id": task_id, "status": "queued"}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to start download")
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")


@router.get("/downloads/{task_id}/status")
async def get_download_status_endpoint(task_id: str):
    """
    Get status and progress of a download task.

    Args:
        task_id: Task identifier

    Returns:
        Download task details including progress history
    """
    try:
        status = spotdl_service.get_download_status(task_id)
        if status is None:
            raise HTTPException(status_code=404, detail="Task not found")
        return status
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get status for {task_id}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/downloads/{task_id}/cancel")
async def cancel_download_endpoint(task_id: str):
    """
    Cancel a running download.

    Args:
        task_id: Task identifier

    Returns:
        {"cancelled": bool}
    """
    try:
        success = await spotdl_service.cancel_download(task_id)
        return {"cancelled": success}
    except Exception as e:
        logger.exception(f"Failed to cancel {task_id}")
        raise HTTPException(status_code=500, detail=str(e))
