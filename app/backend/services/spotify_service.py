"""
Spotify Web API service for fetching user playlists and tracks.
"""

import logging
import time
from typing import List, Optional

import requests

from . import auth_service
from ..models import SpotifyPlaylist, SpotifyTrack

logger = logging.getLogger(__name__)

# Spotify API base URL
SPOTIFY_API_BASE = "https://api.spotify.com/v1"


def _get_auth_headers() -> dict:
    """Build Authorization headers with current access token."""
    token = auth_service.get_valid_access_token()
    if not token:
        raise RuntimeError("Not authenticated with Spotify")
    return {"Authorization": f"Bearer {token}"}


def get_available_playlists(
    limit: int = 50,
    offset: int = 0,
) -> List[SpotifyPlaylist]:
    """
    Fetch user's playlists from Spotify.

    Args:
        limit: Number of playlists to return (max 50)
        offset: Pagination offset

    Returns:
        List of SpotifyPlaylist objects

    Raises:
        requests.HTTPError: On API failure (401, 429, 5xx)
        RuntimeError: If not authenticated
    """
    if limit > 50:
        limit = 50  # Spotify maximum

    url = f"{SPOTIFY_API_BASE}/me/playlists"
    params = {"limit": limit, "offset": offset}

    headers = _get_auth_headers()

    response = requests.get(url, headers=headers, params=params, timeout=10)
    response.raise_for_status()

    data = response.json()
    items = data.get("items", [])

    playlists = []
    for item in items:
        # Extract owner display name
        owner_name = item.get("owner", {}).get("display_name", "Unknown")
        # Track count
        tracks_total = item.get("tracks", {}).get("total", 0)
        # Snapshot ID (for detecting changes)
        snapshot_id = item.get("snapshot_id")

        playlist = SpotifyPlaylist(
            id=item["id"],
            name=item["name"],
            owner=owner_name,
            track_count=tracks_total,
            snapshot_id=snapshot_id,
        )
        playlists.append(playlist)

    return playlists


def get_playlist_tracks(
    playlist_id: str,
    limit: int = 100,
    offset: int = 0,
) -> List[SpotifyTrack]:
    """
    Fetch tracks from a specific playlist.

    Args:
        playlist_id: Spotify playlist ID
        limit: Number of tracks per request (max 100)
        offset: Pagination offset

    Returns:
        List of SpotifyTrack objects

    Raises:
        requests.HTTPError: On API failure (401, 403, 404, 429, 5xx)
        RuntimeError: If not authenticated
    """
    if limit > 100:
        limit = 100  # Spotify maximum

    url = f"{SPOTIFY_API_BASE}/playlists/{playlist_id}/tracks"
    params = {
        "limit": limit,
        "offset": offset,
        "fields": "items(track(id,name,artists(name),album(name,duration_ms,track_number,disc_number,isrc,external_urls,is_local),duration_ms),total",
    }

    headers = _get_auth_headers()

    response = requests.get(url, headers=headers, params=params, timeout=10)
    response.raise_for_status()

    data = response.json()
    items = data.get("items", [])

    tracks = []
    for item in items:
        track_data = item.get("track")
        if not track_data:
            continue  # Skip if track data missing

        # Skip local tracks (not available on Spotify)
        # We still include them but mark as local via minimal data if needed
        is_local = track_data.get("is_local", False)

        # Extract artist names (comma-separated)
        artists_list = track_data.get("artists", [])
        artist_names = [a.get("name", "Unknown") for a in artists_list if a.get("name")]
        artist = ", ".join(artist_names) if artist_names else "Unknown"

        # Album data
        album_data = track_data.get("album", {})
        album_name = album_data.get("name", "Unknown Album")

        # Build SpotifyTrack
        track = SpotifyTrack(
            id=track_data.get("id") or "",  # empty string for local tracks or None
            name=track_data.get("name", "Unknown Track"),
            artist=artist,
            album=album_name,
            duration_ms=track_data.get("duration_ms", 0),
            track_number=track_data.get("track_number"),
            disc_number=track_data.get("disc_number", 1),
            isrc=track_data.get("isrc"),
            external_urls=track_data.get("external_urls"),
        )
        tracks.append(track)

    return tracks


def get_playlist_info(playlist_id: str) -> dict:
    """
    Fetch metadata for a single playlist.

    Args:
        playlist_id: Spotify playlist ID

    Returns:
        Dict with keys: name (str), track_count (int), snapshot_id (str or None)

    Raises:
        requests.HTTPError: On API failure
        RuntimeError: If not authenticated
    """
    url = f"{SPOTIFY_API_BASE}/playlists/{playlist_id}"
    headers = _get_auth_headers()

    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()

    data = response.json()
    name = data.get("name", "Unknown Playlist")
    track_count = data.get("tracks", {}).get("total", 0)
    snapshot_id = data.get("snapshot_id")

    return {
        "name": name,
        "track_count": track_count,
        "snapshot_id": snapshot_id,
    }
