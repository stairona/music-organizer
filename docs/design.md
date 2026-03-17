# Spotify Integration — Data Model & Persistence Design

**Date**: 2026-03-16
**Phase**: 1 of v2.1 (Spotify Desktop App)
**Status**: Draft

---

## 1. Entity Definitions

### 1.1 OAuthTokens

```python
class OAuthTokens:
    access_token: str
    refresh_token: str
    expires_at: datetime  # Unix timestamp or datetime object
```

**Purpose**: Store Spotify OAuth tokens for API authentication. Tokens are obtained via PKCE flow (no client secret). Refresh logic uses `refresh_token` to get new `access_token` when expired.

**Storage table**: `spotify_oauth`
- Single row expected (single-user local app)
- Columns: `id` (INTEGER PRIMARY KEY), `access_token`, `refresh_token`, `expires_at` (INTEGER), `created_at` (INTEGER), `updated_at` (INTEGER)

---

### 1.2 SpotifyPlaylist

```python
class SpotifyPlaylist(BaseModel):
    id: str                    # Spotify playlist ID (URL-safe, e.g., "37i9dQZF1DXcBWIGoYBM5M")
    name: str                  # User-facing playlist name
    owner: str                 # Spotify username of owner
    track_count: int           # Number of tracks in playlist
    snapshot_id: Optional[str] # Playlist version identifier for conditional updates
```

**Purpose**: Read-only representation of a user's playlist for selection in the desktop UI.

**API endpoint**: `GET /spotify/playlists` returns `List[SpotifyPlaylist]`

---

### 1.3 SpotifyTrack

```python
class SpotifyTrack(BaseModel):
    id: str                    # Spotify track ID
    name: str                  # Track title
    artist: str                # Primary artist name
    album: str                 # Album name
    duration_ms: int           # Duration in milliseconds
    track_number: Optional[int]
    disc_number: Optional[int] = 1
    isrc: Optional[str]        # International Standard Recording Code
    external_urls: Optional[Dict[str, str]]  # e.g., {"spotify": "https://..."}
```

**Purpose**: Metadata for tracks within a playlist. Used to construct spotdl download URLs and organize downloaded files.

**API endpoint**: `GET /spotify/playlist/{playlist_id}/tracks` returns `List[SpotifyTrack]`

---

### 1.4 DownloadTask

```python
class DownloadTask(BaseModel):
    task_id: str               # UUID4 or auto-increment integer
    playlist_id: str           # Spotify playlist ID being downloaded
    playlist_name: str         # Snapshot of name at time of download
    destination: str           # Local directory path where files will be saved
    status: str                # "queued" | "downloading" | "completed" | "failed" | "cancelled"
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    total_tracks: int          # Number of tracks in playlist
    completed_tracks: int      # Tracks successfully downloaded
    auto_organize: bool        # Whether to run organize_service after download
    organize_run_id: Optional[str]  # Linked run entry ID from run_history if auto_organized
    error_message: Optional[str]
    spotdl_pid: Optional[int]  # Subprocess PID for cancellation
    progress_percent: float = 0.0
    current_track: Optional[str]  # Track name or "Downloading X of Y"
    created_at: datetime       # Task creation timestamp
```

**Purpose**: Track the lifecycle of a playlist download operation. Enables UI progress display, cancellation, and history.

**Storage table**: `download_tasks`
- Columns: `task_id` (TEXT PRIMARY KEY), `playlist_id`, `playlist_name`, `destination`, `status`, `started_at`, `finished_at`, `total_tracks`, `completed_tracks`, `auto_organize`, `organize_run_id`, `error_message`, `spotdl_pid`, `progress_percent`, `current_track`, `created_at`

---

### 1.5 ProgressSnapshot

```python
class ProgressSnapshot(BaseModel):
    task_id: str
    timestamp: datetime
    percent: float             # 0-100
    current_track: str
    completed_tracks: int
    total_tracks: int
    errors: List[str] = []     # Optional error messages from spotdl
```

**Purpose**: Historical progress records for charting download progress over time, enabling resumable UI charts. Stored separately to avoid bloating main task row.

**Storage table**: `progress_history`
- Columns: `id` (INTEGER PRIMARY KEY), `task_id` (TEXT), `timestamp`, `percent`, `current_track`, `completed_tracks`, `total_tracks`, `errors` (JSON TEXT)

**Indexing**: Index on `task_id` for fast lookups.

---

## 2. Database Schema

### Existing Tables (preserved)
- `run_history` (current store for organize runs)
- `run_progress` (progress entries linked to run_id)

### New Tables (created IF NOT EXISTS)

```sql
-- Spotify OAuth tokens (single row)
CREATE TABLE IF NOT EXISTS spotify_oauth (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    access_token TEXT NOT NULL,
    refresh_token TEXT NOT NULL,
    expires_at INTEGER NOT NULL,  -- Unix timestamp
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);

-- Download tasks
CREATE TABLE IF NOT EXISTS download_tasks (
    task_id TEXT PRIMARY KEY,
    playlist_id TEXT NOT NULL,
    playlist_name TEXT NOT NULL,
    destination TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('queued', 'downloading', 'completed', 'failed', 'cancelled')),
    started_at INTEGER,  -- Unix timestamp, NULLABLE
    finished_at INTEGER, -- Unix timestamp, NULLABLE
    total_tracks INTEGER NOT NULL,
    completed_tracks INTEGER NOT NULL DEFAULT 0,
    auto_organize BOOLEAN NOT NULL DEFAULT 1,
    organize_run_id TEXT,  -- References run_history.run_id (if any)
    error_message TEXT,
    spotdl_pid INTEGER,
    progress_percent REAL NOT NULL DEFAULT 0.0,
    current_track TEXT,
    created_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_download_tasks_created ON download_tasks(created_at DESC);

-- Progress history (many snapshots per task)
CREATE TABLE IF NOT EXISTS progress_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    timestamp INTEGER NOT NULL,  -- Unix timestamp
    percent REAL NOT NULL,
    current_track TEXT NOT NULL,
    completed_tracks INTEGER NOT NULL,
    total_tracks INTEGER NOT NULL,
    errors TEXT,  -- JSON array as TEXT
    FOREIGN KEY (task_id) REFERENCES download_tasks(task_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_progress_history_task_id ON progress_history(task_id);
```

---

## 3. Store Functions (app/backend/store/__init__.py)

### OAuth Functions

- `get_oauth_tokens() -> Optional[OAuthTokens]`
- `save_oauth_tokens(tokens: OAuthTokens) -> None`
- `delete_oauth_tokens() -> None`

### Download Task Functions

- `create_download_task(task: DownloadTask) -> None`  (INSERT)
- `get_download_task(task_id: str) -> Optional[DownloadTask]`
- `update_download_task(task_id: str, updates: Dict[str, Any]) -> None`  (partial UPDATE)
- `list_download_tasks(limit: int = 50, status_filter: Optional[str] = None) -> List[DownloadTask]`
- `delete_download_task(task_id: str) -> None`  (for cleanup)
- `cancel_download_task(task_id: str) -> None`  (sets status = 'cancelled', clears PID)

### Progress Snapshot Functions

- `add_progress_snapshot(snapshot: ProgressSnapshot) -> None`
- `get_progress_history(task_id: str) -> List[ProgressSnapshot]`
- `clear_progress_history(task_id: str) -> None`  (on task delete)

---

## 4. Foreign Key Relationships

- `download_tasks.organize_run_id` → `run_history.run_id` (optional)
  - Enables tracing: which organize run was triggered by which download
  - Should be set when `auto_organize=True` and organize service completes

- `progress_history.task_id` → `download_tasks.task_id` (ON DELETE CASCADE)
  - When a task is deleted (manual cleanup), its progress snapshots are removed automatically.

---

## 5. Migration Strategy

- Store functions use `CREATE TABLE IF NOT EXISTS` so existing installations get new tables automatically on first run.
- No data migration needed (new tables only).
- Future schema changes should use `ALTER TABLE ADD COLUMN` with default values for backward compatibility.

---

## 6. Testing Plan

### test_models_spotify.py
- Pydantic model instantiation with required/optional fields
- JSON serialization/deserialization
- Default value handling (e.g., `auto_organize=True`, `progress_percent=0.0`)
- Validation errors for missing required fields

### test_store_spotify.py
- In-memory SQLite database (`:memory:`) for isolation
- CRUD operations for `spotify_oauth` (insert, get, update, delete)
- Create/read/update/list for `download_tasks`
- Progress snapshot insertion and retrieval
- Foreign key cascade deletion (progress_history when task deleted)
- Transaction safety (rollback on error)
- Schema introspection to verify tables exist

---

## 7. Security & Privacy Considerations

- OAuth tokens stored in same directory as existing `config.json` (`~/.config/music-organizer/`).
- File permissions: rely on OS defaults (user-only readable) or chmod 600 if paranoid.
- **Note**: For Phase 2+, consider encrypting tokens with `cryptography.Fernet` using a key derived from user-specific secret (e.g., macOS Keychain, or prompt on startup). Not required for MVP.
- spotdl subprocess runs with same user permissions; no elevation.

---

## 8. Performance Considerations

- Index on `download_tasks.created_at DESC` for fast history queries (show recent first).
- Index on `progress_history.task_id` for quick lookup when rendering progress charts.
- `progress_history` could grow large; consider periodic cleanup (delete snapshots older than 90 days) in a future maintenance phase.
- All stores operate on local SQLite file; no network latency.

---

## 9. Error Handling & Edge Cases

- **Token expiry**: `expires_at` checked before each Spotify API call; auto-refresh if within 5-minute window.
- **Task not found**: Return `None` or raise `KeyError` depending on function (documented).
- **Concurrent access**: SQLite handles single-writer fine; if desktop app and CLI both run, they may contend. Acceptable for MVP; file-locking handled by SQLite.
- **Partial updates**: `update_download_task()` accepts dict; only specified columns updated. Allows concurrent progress updates without overwriting.

---

## 10. Alignment with Upgraded Plan

This design satisfies Phase 1 requirements from `.UPGRADED_PLAN.md`:
- ✅ Data models documented
- ✅ Pydantic models in `models/__init__.py`
- ✅ Storage schema in `store/__init__.py` (new tables, backward-compatible)
- ✅ Helper functions in store layer
- ✅ Unit tests for models and store

**Next**: After Phase 1 review, proceed to Phase 2 (Spotify Authentication Service).
