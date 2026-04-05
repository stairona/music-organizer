"""
spotdl orchestration service: download Spotify playlists via spotdl CLI.
"""

import asyncio
import logging
import os
import re
import signal
import subprocess
import time
from typing import Dict, Optional

from ..store import (
    create_download_task,
    update_download_task,
    add_progress_snapshot,
    get_download_task,
    get_progress_history,
)
from . import organize_service

logger = logging.getLogger(__name__)

# Global registry of running subprocesses (task_id -> asyncio.subprocess.Process)
# Note: This works for single-process desktop app; not suitable for multi-worker deployment.
_running_processes: Dict[str, asyncio.subprocess.Process] = {}


def _extract_percentage(line: str) -> Optional[float]:
    """
    Extract a percentage (0-100) from spotdl stdout line.
    spotdl may output: "[download]  50.0% of ~10.00MiB" or "100%"
    """
    # Look for patterns like "50.0%" or "100%"
    match = re.search(r"(\d+(?:\.\d+)?)%", line)
    if match:
        try:
            pct = float(match.group(1))
            if 0 <= pct <= 100:
                return pct
        except ValueError:
            pass
    return None


def _extract_filename(line: str) -> Optional[str]:
    """
    Try to extract filename from spotdl output.
    Example: "Downloaded: /path/to/song.mp3" or "Processing: Song Name"
    """
    # Look for common patterns
    patterns = [
        r"Downloaded:\s+(.+\.mp3)",  # Downloaded: /path/file.mp3
        r"Saving:\s+(.+\.mp3)",      # Saving: file.mp3
        r"Processing:\s+(.+)",       # Processing: Song Name
        r"Downloading\s+(.+?)(?:\s|$)",  # Downloading Song Name
    ]
    for pat in patterns:
        match = re.search(pat, line, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


def _extract_playlist_name(line: str) -> Optional[str]:
    """
    Extract playlist name from spotdl output.
    spotdl outputs: "Playlist: My Playlist Name" or "Downloading playlist: My Playlist"
    """
    patterns = [
        r"Playlist:\s+(.+)",
        r"Downloading playlist:\s+(.+)",
        r"Fetching playlist:\s+(.+)",
    ]
    for pat in patterns:
        match = re.search(pat, line, re.IGNORECASE)
        if match:
            name = match.group(1).strip()
            # Clean up any trailing punctuation
            name = name.rstrip(" .")
            return name
    return None


def _extract_total_tracks(line: str) -> Optional[int]:
    """
    Extract total track count from spotdl output.
    spotdl outputs: "Found 150 tracks" or "Total tracks: 150" or "150 songs"
    """
    patterns = [
        r"Found\s+(\d+)\s+(?:tracks?|songs?)",
        r"Total\s+(?:tracks?|songs?):\s*(\d+)",
        r"(\d+)\s+(?:tracks?|songs?)\s+(?:in|total)",
    ]
    for pat in patterns:
        match = re.search(pat, line, re.IGNORECASE)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                pass
    return None


async def _read_stream(stream, task_id: str, total_tracks: int):
    """
    Async read lines from subprocess stdout, parse progress, update store.
    """
    buffer = ""
    last_percent = 0.0
    completed_tracks = 0

    while True:
        chunk = await stream.read(1024)
        if not chunk:
            break
        buffer += chunk.decode("utf-8", errors="ignore")
        lines = buffer.split("\n")
        # Keep last partial line in buffer
        buffer = lines[-1]
        for line in lines[:-1]:
            line = line.strip()
            if not line:
                continue

            # Extract playlist name if found
            playlist_name = _extract_playlist_name(line)
            if playlist_name:
                try:
                    update_download_task(task_id, {"playlist_name": playlist_name})
                except Exception as e:
                    logger.error(f"Failed to update playlist_name: {e}")

            # Extract total tracks if found (only set if we currently have 0)
            extracted_total = _extract_total_tracks(line)
            if extracted_total and total_tracks == 0:
                total_tracks = extracted_total
                try:
                    update_download_task(task_id, {"total_tracks": total_tracks})
                except Exception as e:
                    logger.error(f"Failed to update total_tracks: {e}")

            # Parse percentage
            pct = _extract_percentage(line)
            if pct is not None and pct != last_percent:
                last_percent = pct
                # Estimate completed tracks from percentage and total_tracks
                if total_tracks > 0:
                    completed_tracks = int((pct / 100) * total_tracks)
                else:
                    # If total unknown, we can't compute completed tracks; keep 0
                    completed_tracks = 0

                # Update task progress
                try:
                    update_download_task(task_id, {
                        "progress_percent": last_percent,
                        "completed_tracks": completed_tracks,
                    })
                    add_progress_snapshot(
                        task_id=task_id,
                        percent=last_percent,
                        current_track=line[:200],  # store a snippet
                        completed_tracks=completed_tracks,
                        total_tracks=total_tracks,
                    )
                except Exception as e:
                    logger.error(f"Failed to update progress: {e}")

            # Optionally extract filename for current_track field
            filename = _extract_filename(line)
            if filename:
                try:
                    update_download_task(task_id, {"current_track": filename})
                except Exception as e:
                    logger.error(f"Failed to update current_track: {e}")


async def download_playlist(
    playlist_id: str,
    destination: str,
    task_id: str,
    auto_organize: bool = True,
    format: str = "mp3",
    quality: str = "320k",
) -> None:
    """
    Download a Spotify playlist using spotdl.

    Args:
        playlist_id: Spotify playlist ID
        destination: Local directory to save files
        task_id: Unique task identifier (already created in store)
        auto_organize: Whether to run organize_service after download
        format: Audio format (default mp3)
        quality: Bitrate quality (default 320k)

    Raises:
        Exception: On download failure (subprocess error, API failure)
    """
    # Ensure destination exists
    os.makedirs(destination, exist_ok=True)

    # Update task status to downloading (playlist_name and total_tracks will be set via log parsing)
    try:
        update_download_task(task_id, {
            "status": "downloading",
            "started_at": int(time.time()),
        })
    except Exception as e:
        logger.error(f"Failed to update task start: {e}")

    # Construct spotdl command using the playlist ID (spotdl accepts URL or ID)
    playlist_url = f"https://open.spotify.com/playlist/{playlist_id}"
    cmd = [
        "spotdl",
        playlist_url,
        "--format", format,
        "--quality", quality,
        "--output", destination,
        "--log-level", "INFO",
    ]

    logger.info(f"Starting spotdl download: {' '.join(cmd)}")

    # Spawn subprocess
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        # Store PID for cancellation
        try:
            update_download_task(task_id, {"spotdl_pid": proc.pid})
            _running_processes[task_id] = proc
        except Exception as e:
            logger.error(f"Failed to store PID: {e}")

        # Start stdout reader
        try:
            await _read_stream(proc.stdout, task_id, total_tracks)
        except Exception as e:
            logger.error(f"Error reading stdout: {e}")

        # Wait for process to exit
        returncode = await proc.wait()
        logger.info(f"spotdl exited with code {returncode}")

        # Clean up registry
        _running_processes.pop(task_id, None)

        # Fetch the final task state to get updated total_tracks from log parsing
        try:
            final_task = get_download_task(task_id)
            final_total_tracks = final_task.get("total_tracks", 0) if final_task else 0
        except Exception as e:
            logger.error(f"Failed to fetch final task state: {e}")
            final_total_tracks = 0

        # Update task final status
        finished_at = int(time.time())
        if returncode == 0:
            try:
                update_download_task(task_id, {
                    "status": "completed",
                    "progress_percent": 100.0,
                    "completed_tracks": final_total_tracks,
                    "finished_at": finished_at,
                })
                add_progress_snapshot(
                    task_id=task_id,
                    percent=100.0,
                    current_track="Download complete",
                    completed_tracks=final_total_tracks,
                    total_tracks=final_total_tracks,
                )
                logger.info(f"Download task {task_id} completed successfully")
            except Exception as e:
                logger.error(f"Failed to mark completed: {e}")
        else:
            error_msg = f"spotdl exited with code {returncode}"
            try:
                update_download_task(task_id, {
                    "status": "failed",
                    "error_message": error_msg,
                    "finished_at": finished_at,
                })
                logger.error(f"Download task {task_id} failed: {error_msg}")
            except Exception as e:
                logger.error(f"Failed to mark failed: {e}")

        # If auto_organize, trigger organize_service
        if returncode == 0 and auto_organize:
            try:
                logger.info(f"Auto-organizing downloaded files in {destination}")
                # Use conservative options: general level, default profile
                result = organize_service(
                    source=destination,
                    destination=destination,  # organize in-place
                    mode="move",  # move files into genre folders within destination
                    level="general",
                    profile="default",
                    dry_run=False,
                    skip_existing=False,
                )
                # Store organize run_id for traceability
                # We need to get the run_id from the most recent run? organize_service creates a run internally.
                # For now, we won't store run_id. Can be added later if needed.
                logger.info(f"Organize service completed: {result.summary}")
            except Exception as e:
                logger.error(f"Auto-organize failed: {e}")

    except Exception as e:
        logger.exception(f"Download failed: {e}")
        try:
            update_download_task(task_id, {
                "status": "failed",
                "error_message": str(e),
                "finished_at": int(time.time()),
            })
        except Exception:
            pass
        raise


async def cancel_download(task_id: str) -> bool:
    """
    Cancel a running download.

    Args:
        task_id: Task identifier

    Returns:
        True if cancelled, False if not found or already finished
    """
    proc = _running_processes.get(task_id)
    if not proc:
        return False

    try:
        proc.terminate()
        # Give it 5 seconds to exit gracefully
        try:
            await asyncio.wait_for(proc.wait(), timeout=5)
        except asyncio.TimeoutError:
            # Force kill
            proc.kill()
            await proc.wait()
        _running_processes.pop(task_id, None)
        # Update task status
        update_download_task(task_id, {
            "status": "cancelled",
            "finished_at": int(time.time()),
        })
        logger.info(f"Download task {task_id} cancelled")
        return True
    except Exception as e:
        logger.error(f"Failed to cancel task {task_id}: {e}")
        return False


def get_download_status(task_id: str) -> Optional[Dict]:
    """
    Get current status of a download task.

    Returns:
        Dict with task details and recent progress history, or None if not found
    """
    task = get_download_task(task_id)
    if not task:
        return None

    # Fetch recent progress snapshots (last 50)
    history = get_progress_history(task_id)
    recent = history[-50:] if len(history) > 50 else history

    return {
        "task_id": task["task_id"],
        "status": task["status"],
        "playlist_id": task["playlist_id"],
        "playlist_name": task["playlist_name"],
        "destination": task["destination"],
        "total_tracks": task["total_tracks"],
        "completed_tracks": task["completed_tracks"],
        "progress_percent": task["progress_percent"],
        "current_track": task["current_track"],
        "auto_organize": bool(task["auto_organize"]),
        "spotdl_pid": task["spotdl_pid"],
        "error_message": task["error_message"],
        "started_at": task["started_at"],
        "finished_at": task["finished_at"],
        "progress_history": recent,
    }
