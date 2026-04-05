"""
API route handlers.
"""

import asyncio
import logging
import re
import uuid
from typing import Optional
from fastapi import APIRouter, HTTPException, Body
from ..services import analyze_service, organize_service, spotdl_service
from ..store import (
    create_download_task,
    update_download_task,
    add_progress_snapshot,
    get_download_task,
    get_progress_history,
    list_download_tasks,
)
from ..models import (
    AnalyzeRequest,
    OrganizeRequest,
    AnalyzeResult,
    OrganizeResult,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["api"])


def _extract_playlist_id(playlist_url: str) -> str:
    """
    Extract Spotify playlist ID from various URL formats.
    Supports:
      - https://open.spotify.com/playlist/{id}
      - spotify:playlist:{id}
      - raw ID (36-character alphanumeric)
    Returns the playlist ID string.
    Raises ValueError if ID cannot be extracted.
    """
    # Clean whitespace
    url = playlist_url.strip()

    # Try matching open.spotify.com URL
    m = re.search(r"open\.spotify\.com/playlist/([a-zA-Z0-9]+)", url)
    if m:
        return m.group(1)

    # Try matching spotify:playlist: URI
    m = re.search(r"spotify:playlist:([a-zA-Z0-9]+)", url)
    if m:
        return m.group(1)

    # If it looks like a raw ID (at least 20 alphanumeric chars)
    if re.fullmatch(r"[a-zA-Z0-9]{20,}", url):
        return url

    raise ValueError(f"Invalid Spotify playlist URL or ID: {playlist_url}")


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


# --- Download Routes (Simplified, no auth) ---

from ..models import DownloadTask


@router.post("/downloads")
async def start_download(
    playlist_url: str = Body(..., embed=True),
    destination: str = Body(..., embed=True),
):
    """
    Start downloading a Spotify playlist via spotdl.

    Args:
        playlist_url: Spotify playlist URL or ID (e.g., https://open.spotify.com/playlist/... or spotify:playlist:...)
        destination: Local directory to save files

    Returns:
        {"task_id": str, "status": "queued"}
    """
    try:
        # Extract playlist ID from URL
        try:
            playlist_id = _extract_playlist_id(playlist_url)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        # No authentication required

        # Create a unique task ID
        task_id = str(uuid.uuid4())

        # Initialize with empty/zero values; will be populated from spotdl output
        playlist_name = ""  # Will be extracted from spotdl logs
        total_tracks = 0    # Will be updated once spotdl reports track count
        auto_organize = False  # Manual organize only (per user decision)

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


@router.get("/downloads")
async def list_downloads(
    limit: int = 50,
    status: Optional[str] = None
):
    """
    List download tasks (history).

    Args:
        limit: Maximum number of tasks to return (default 50)
        status: Optional filter by status ('queued', 'downloading', 'completed', 'failed', 'cancelled')

    Returns:
        List of download task dicts (most recent first)
    """
    try:
        tasks = list_download_tasks(limit=limit, status_filter=status)
        return tasks
    except Exception as e:
        logger.exception(f"Failed to list downloads")
        raise HTTPException(status_code=500, detail=str(e))
