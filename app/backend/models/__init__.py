"""
Data models for the Music Organizer API.
"""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any, Literal
from datetime import datetime


class AnalyzeRequest(BaseModel):
    """Request model for library analysis."""
    source: str = Field(..., description="Root folder of the music library to scan")
    level: Literal["general", "specific", "both"] = Field("general", description="Classification level")
    limit: Optional[int] = Field(None, description="Limit number of files to process")
    exclude_dir: Optional[List[str]] = Field(None, description="Directory names to skip")


class OrganizeRequest(BaseModel):
    """Request model for organizing files."""
    source: str = Field(..., description="Root folder of the music library")
    destination: str = Field(..., description="Destination root for organized files")
    mode: Literal["copy", "move"] = Field("copy", description="File operation")
    level: Literal["general", "specific", "both"] = Field("general", description="Classification level")
    profile: Literal["default", "cdj-safe"] = Field("default", description="Output profile")
    dry_run: bool = Field(False, description="Preview without making changes")
    skip_existing: bool = Field(False, description="Skip files that already exist at destination")
    skip_unknown_only: bool = Field(False, description="Process only files classified as Unknown")
    on_collision: Literal["hash", "skip", "rename"] = Field("hash", description="Collision policy")
    limit: Optional[int] = Field(None, description="Limit number of files")
    exclude_dir: Optional[List[str]] = Field(None, description="Directories to skip")


class RunSummary(BaseModel):
    """Summary statistics for a run."""
    total: int
    processed: int
    moved_or_copied: int
    unknown_count: int
    reason_counts: Dict[str, int]
    specific_counter: Dict[str, int]
    general_counter: Dict[str, int]
    skipped_counts: Optional[Dict[str, int]] = None


class UnknownDiagnostics(BaseModel):
    """Information about files that could not be classified."""
    count: int
    sample_paths: List[str] = Field(default_factory=list)


class AnalyzeResult(BaseModel):
    """Response model for analysis."""
    success: bool
    summary: RunSummary
    unknown_diagnostics: Optional[UnknownDiagnostics] = None
    csv_report_path: Optional[str] = None


class OrganizeResult(BaseModel):
    """Response model for organization."""
    success: bool
    summary: RunSummary
    unknown_diagnostics: Optional[UnknownDiagnostics] = None
    csv_report_path: Optional[str] = None
    journal_saved: bool = False
    warnings: List[str] = Field(default_factory=list)


class ProgressEvent(BaseModel):
    """Event model for streaming progress updates."""
    event_type: str  # e.g., "scan_complete", "classification_progress", "file_processed"
    data: Dict[str, Any]


# --- Run History Models ---

class FileOperation(BaseModel):
    """Record of a single file operation within a run."""
    source: str
    destination: str
    # Could add: classification (specific, general, reason), result (copied/moved/skipped)


class RunEntry(BaseModel):
    """Metadata for a single organize run (lightweight, excludes full entries)."""
    run_id: str
    started_at: str  # ISO datetime
    finished_at: Optional[str] = None
    source: str
    destination: str
    status: str  # running/completed/cancelled/failed
    options: Dict[str, Any]
    summary: Optional[Dict[str, Any]] = None  # RunSummary as dict


class FullRunEntry(RunEntry):
    """Full run entry including per-file records."""
    entries: List[FileOperation] = Field(default_factory=list)


class UndoResult(BaseModel):
    """Result of an undo operation."""
    reverted: int
    failed: int
    errors: List[str] = Field(default_factory=list)


# --- Spotify Integration Models ---


class OAuthTokens(BaseModel):
    """Spotify OAuth tokens for API authentication."""
    access_token: str
    refresh_token: str
    expires_at: int  # Unix timestamp


class SpotifyPlaylist(BaseModel):
    """Spotify playlist metadata (read-only)."""
    id: str
    name: str
    owner: str
    track_count: int
    snapshot_id: Optional[str] = None


class SpotifyTrack(BaseModel):
    """Spotify track metadata."""
    id: str
    name: str
    artist: str
    album: str
    duration_ms: int
    track_number: Optional[int] = None
    disc_number: Optional[int] = 1
    isrc: Optional[str] = None
    external_urls: Optional[Dict[str, str]] = None


class DownloadTask(BaseModel):
    """Track a playlist download operation."""
    task_id: str
    playlist_id: str
    playlist_name: str
    destination: str
    status: Literal["queued", "downloading", "completed", "failed", "cancelled"]
    started_at: Optional[int] = None  # Unix timestamp
    finished_at: Optional[int] = None  # Unix timestamp
    total_tracks: int
    completed_tracks: int = 0
    auto_organize: bool = True
    organize_run_id: Optional[str] = None
    error_message: Optional[str] = None
    spotdl_pid: Optional[int] = None
    progress_percent: float = 0.0
    current_track: Optional[str] = None
    created_at: Optional[int] = None  # Unix timestamp; auto-filled by store if None


class ProgressSnapshot(BaseModel):
    """Historical progress record for a download task."""
    task_id: str
    timestamp: int  # Unix timestamp
    percent: float
    current_track: str
    completed_tracks: int
    total_tracks: int
    errors: List[str] = Field(default_factory=list)
