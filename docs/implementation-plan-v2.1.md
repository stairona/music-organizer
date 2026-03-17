# v2.1 Implementation Plan: Spotify Desktop App
## Detailed Execution Plan for Phases 3-7

**Date**: 2026-03-16
**Status**: Phase 1 & 2 Complete | Phase 3 Ready to Start
**Current Branch**: `main`
**Next Branch**: `feature/spotify-v2.1-phases-3-7` (create before starting)

---

## ✅ Completed Work Summary

| Phase | Name | Status | Tests |
|-------|------|--------|-------|
| 0 | v2.0 Baseline | ✅ Complete | 132 |
| 1 | Data Models & Persistence | ✅ Complete | +34 (166 total) |
| 2 | OAuth PKCE Authentication | ✅ Complete | +29 (195 total) |

**Commits pushed**: `92fc8b1`, `9b713bf`, `076f8c8`
**Test status**: 195 passing

---

## 📌 Immediate Next: Phase 3 — Spotify Playlist Service

**Estimated**: 2-4 hours
**Goal**: Fetch authenticated user's Spotify playlists

### Step-by-Step Implementation

#### 1. Create `app/backend/services/spotify_service.py`

**Functions to implement**:

```python
def get_available_playlists(
    limit: int = 50,
    offset: int = 0
) -> List[SpotifyPlaylist]:
    """
    Fetch user's playlists from Spotify API.

    Args:
        limit: Max playlists to return (Spotify max 50)
        offset: Pagination offset

    Returns:
        List of SpotifyPlaylist models

    Raises:
        HTTPError on API failure
    """
    # Implementation:
    # 1. Get access token: token = auth_service.get_valid_access_token()
    #    - if None: raise HTTPException(401, "Not authenticated")
    # 2. Make GET request to Spotify API:
    #    URL: f"https://api.spotify.com/v1/me/playlists?limit={limit}&offset={offset}"
    #    Headers: {"Authorization": f"Bearer {token}"}
    # 3. Parse response JSON:
    #    - items: [{id, name, owner: {display_name}, tracks: {total}, snapshot_id}]
    # 4. Convert to SpotifyPlaylist model list
    # 5. Return list
```

**Key details**:
- Use `requests.get()` with timeout=10
- Handle pagination (but for MVP just return first 50)
- Error handling: 401 → try refresh once, then fail; 403/429 → rate limit
- Filter: include only playlists user can access (owner or collaborative)
- **Note**: For "owner", use `playlist['owner']['display_name']` (not just owner id)

```python
def get_playlist_tracks(
    playlist_id: str,
    limit: int = 100,
    offset: int = 0
) -> List[SpotifyTrack]:
    """
    Fetch tracks from a specific playlist.

    Args:
        playlist_id: Spotify playlist ID
        limit: Max tracks per request (Spotify max 100)
        offset: Pagination offset

    Returns:
        List of SpotifyTrack models

    Raises:
        HTTPError on API failure
    """
    # Implementation:
    # 1. Get access token (same as above)
    # 2. GET https://api.spotify.com/v1/playlists/{playlist_id}/tracks
    #    Params: ?limit={limit}&offset={offset}
    # 3. Parse response:
    #    - items: [{track: {id, name, artists: [{name}], album: {name}, duration_ms, track_number, disc_number, isrc, external_urls}}]
    # 4. Map to SpotifyTrack:
    #    - artist: join artist names with ", " if multiple
    #    - track_number, disc_number may be None if missing
    # 5. Return list
```

**Key details**:
- Artists field is an array; join primary artists (limit to 3, comma-separated)
- Some tracks may have `is_local: true` (skip them in response? Or include with placeholder?)
- Duration is in ms; keep as-is
- If track is not available (due to region restrictions), it may have `is_local: true`; still include it with minimal data

#### 2. Add API Routes in `app/backend/routes/__init__.py`

```python
from ..services import spotify_service

router = APIRouter(prefix="/api/v1", tags=["api"])

# Add these endpoints

@router.get("/spotify/playlists")
async def spotify_playlists(limit: int = 50):
    """
    List user's Spotify playlists.
    Requires Spotify authentication.
    """
    try:
        playlists = spotify_service.get_available_playlists(limit=limit)
        return {"playlists": [p.model_dump() for p in playlists]}
    except requests.HTTPError as e:
        if e.response.status_code == 401:
            raise HTTPException(status_code=401, detail="Not authenticated")
        raise HTTPException(status_code=500, detail="Spotify API error")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/spotify/playlist/{playlist_id}/tracks")
async def spotify_playlist_tracks(
    playlist_id: str,
    limit: int = 100,
    offset: int = 0
):
    """
    Get tracks from a specific playlist.
    """
    try:
        tracks = spotify_service.get_playlist_tracks(
            playlist_id=playlist_id,
            limit=limit,
            offset=offset
        )
        return {"tracks": [t.model_dump() for t in tracks]}
    except requests.HTTPError as e:
        if e.response.status_code in (401, 403):
            raise HTTPException(status_code=e.response.status_code, detail="Access denied")
        raise HTTPException(status_code=500, detail="Spotify API error")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

**Imports needed**:
- `import requests` (for catching `requests.HTTPError`)
- `from ..services import spotify_service`

#### 3. Create Unit Tests

**File**: `tests/test_spotify_service.py`

Structure:

```python
import pytest
from unittest.mock import Mock, patch
from app.backend.services import spotify_service
from app.backend.models import SpotifyPlaylist, SpotifyTrack

class TestGetAvailablePlaylists:
    @patch("app.backend.services.spotify_service.requests.get")
    @patch("app.backend.services.spotify_service.auth_service.get_valid_access_token")
    def test_returns_playlist_list(self, mock_token, mock_get):
        mock_token.return_value = "test_token"
        mock_response = Mock()
        mock_response.json.return_value = {
            "items": [
                {
                    "id": "pl1",
                    "name": "My Playlist",
                    "owner": {"display_name": "user123"},
                    "tracks": {"total": 50},
                    "snapshot_id": "abc"
                }
            ],
            "total": 1
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        playlists = spotify_service.get_available_playlists()
        assert len(playlists) == 1
        assert isinstance(playlists[0], SpotifyPlaylist)
        assert playlists[0].name == "My Playlist"

    @patch("app.backend.services.spotify_service.auth_service.get_valid_access_token")
    def test_raises_if_not_authenticated(self, mock_token):
        mock_token.return_value = None
        with pytest.raises(HTTPException) as exc_info:
            spotify_service.get_available_playlists()
        assert exc_info.value.status_code == 401

    @patch("app.backend.services.spotify_service.requests.get")
    @patch("app.backend.services.spotify_service.auth_service.get_valid_access_token")
    def test_handles_http_errors(self, mock_token, mock_get):
        mock_token.return_value = "token"
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("403 Forbidden")
        mock_get.return_value = mock_response

        with pytest.raises(requests.HTTPError):
            spotify_service.get_available_playlists()

class TestGetPlaylistTracks:
    # Similar structure
    @patch("app.backend.services.spotify_service.requests.get")
    @patch("app.backend.services.spotify_service.auth_service.get_valid_access_token")
    def test_returns_track_list(self, mock_token, mock_get):
        # Mock response with various track scenarios
        pass

    def test_artist_join_logic(self):
        # Test that multiple artists are joined correctly
        # mock a track with artists=[{"name": "A"}, {"name": "B"}]
        # verify result.artist == "A, B"
```

**Tip**: Use `SpotifyPlaylist.model_validate()` to construct from dict.

#### 4. Create Route Tests

**File**: `tests/test_spotify_routes.py`

```python
from fastapi.testclient import TestClient
from app.backend.main import app

client = TestClient(app)

class TestSpotifyPlaylists:
    @patch("app.backend.routes.spotify_service.get_available_playlists")
    def test_success_returns_playlist_list(self, mock_service):
        from app.backend.models import SpotifyPlaylist
        mock_service.return_value = [
            SpotifyPlaylist(id="p1", name="Test", owner="user", track_count=10)
        ]
        response = client.get("/api/v1/spotify/playlists")
        assert response.status_code == 200
        assert response.json()["playlists"][0]["name"] == "Test"

    @patch("app.backend.routes.spotify_service.get_available_playlists")
    def test_error_returns_500(self, mock_service):
        mock_service.side_effect = Exception("API error")
        response = client.get("/api/v1/spotify/playlists")
        assert response.status_code == 500

class TestSpotifyPlaylistTracks:
    # Similar for /spotify/playlist/{id}/tracks
    pass
```

#### 5. Verify All Tests Pass

```bash
python -m pytest tests/test_spotify_service.py tests/test_spotify_routes.py -v
python -m pytest tests/ -q  # Full suite, expect 195+ passing
```

#### 6. Manual Smoke Test (Optional but Recommended)

```bash
# Terminal 1: start backend
export SPOTIPY_CLIENT_ID="your_client_id"
uvicorn app.backend.main:app --reload

# Terminal 2: use curl or httpie to test
# First, go through auth flow with /auth/spotify/login
# Then:
# curl http://localhost:8000/api/v1/spotify/playlists
```

**Note**: You can get a Spotify client ID from https://developer.spotify.com/dashboard

---

## 🔄 Plan for Phases 4-7 (High-Level)

After Phase 3, proceed with:

### Phase 4 — spotdl Orchestration (6-12 hours)
- Research: `spotdl --help`, parse stdout (look for `[download]`, `[download] 100%`)
- `services/spotdl_service.py`:
  - `class SpotDLOrchestrator` with `download_playlist(playlist_url, dest_dir, task_id)`
  - Spawn subprocess: `subprocess.Popen(['spotdl', playlist_url, '--format', 'mp3', '--quality', '320k', '--output', dest_dir], ...)`
  - Parse stdout line-by-line; look for progress percentage; update progress store
  - `cancel_download(task_id)` → `proc.terminate()` (or `kill()` if needed)
  - Handle errors: non-zero exit code, OSError, timeout
- Add routes: `POST /downloads`, `GET /downloads/{id}/status`, `POST /downloads/{id}/cancel`
- Update store: add `spotdl_pid`, `status` transitions
- Tests: mock `subprocess.Popen` with fake stdout generator

### Phase 5 — Organize Bridge (2-4 hours)
- In `spotdl_service.download_playlist()` after subprocess exits with code 0:
  - If `auto_organize=True` (from task record), call `organize_service(dest_dir, ...)` synchronously
  - Store returned `run_id` in `download_tasks.organize_run_id`
- Add `auto_organize` column to `download_tasks` (already in model)
- Tests: verify `organize_service` is called with correct dest_dir and options

### Phase 6 — Desktop App (8-16 hours)
- Decision: **Tauri** (Rust, smaller) or **Electron** (JS-only, more familiar)
  - Recommend Tauri for production quality; Electron for speed
- Create `desktop/` with framework starter
- Backend spawn: `python -m app.backend.main` (uvicorn programmatically)
- CORS: `app.add_middleware(CORSMiddleware, allow_origins=["electron://*", "tauri://*"])`
- UI pages:
  - Login: "Connect Spotify" button → GET `/auth/spotify/login` → open system browser
  - Callback handling: intercept `http://localhost:8080/callback` with code → POST `/auth/spotify/callback`
  - Playlist select: GET `/spotify/playlists` → table with checkboxes → "Download" button
  - Downloads: poll GET `/downloads/{id}/status` every 2s; show progress bar; cancel button
  - History: GET `/downloads?limit=20` from `download_tasks`
- Build & package for macOS (dmg)

### Phase 7 — Validation & Hardening (4-8 hours)
- Integration test: mock entire flow (login→playlists→download→organize)
- Add token refresh retry (3 attempts with exponential backoff)
- Add spotdl timeout (per track: 5min; overall: customizable)
- Pre-download disk space check: estimate ~320kbps × duration_ms / 8
- Rate limiting: simple `time.sleep(1)` between Spotify API calls
- Structured logging: JSON format to `~/.config/music-organizer/spotify.log`
- Update CLI `config` command to show Spotify status: `music-organizer config --show spotify`
- Update CHANGELOG.md v2.1.0
- Final test run: all 195+ tests must pass

---

## 🧪 Testing Strategy

All new code must have ≥90% coverage. Mock external calls.

### Spotify Service Tests
- Mock `requests.get` with fixture JSON responses
- Test: construct `SpotifyPlaylist` from API response shape
- Test: artist joining logic
- Test: pagination (limit/offset passthrough)
- Test: HTTP errors (401, 429, 500)
- Test: malformed responses (missing fields)

### spotdl Service Tests
- Mock `subprocess.Popen` with fake process object
- Simulate stdout stream with progress markers
- Test: progress parsing regex patterns
- Test: cancellation sets state to "cancelled"
- Test: non-zero exit code → status "failed"
- Test: timeout kills process and marks failed
- Test: disk full OSError handling

### Integration Test (1 golden flow)
- Fixtures: `playlists_response.json`, `tracks_response.json`
- Mock auth_service.get_valid_access_token → "token"
- Mock spotify_service.get_available_playlists → returns fixtures
- Mock spotdl_service → immediate success (create dummy files)
- Run through: create task → download → organize → complete
- Assert: task status transitions, organize_run_id set, progress recorded

---

## 📦 Dependencies to Add

**requirements.txt** (append):
```
# Spotify API
requests>=2.31.0  # HTTP client

# spotdl subprocess management
psutil>=5.9.0     # For process tree killing

# Optional: encryption (future)
# cryptography>=41.0.0
```

---

## ⚠️ Key Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Spotify API rate limits (429) | Medium | High | Implement simple 1s delay between calls; detect 429 and retry with backoff |
| spotdl stdout format changes | High | High | Pin spotdl version in requirements; use regex that tolerates minor changes; implement fallback parser |
| Large playlist downloads (>100 tracks) cause memory issues | Medium | Medium | Stream processing; progress updates every track; limit to 50 tracks per download for MVP |
| OAuth token expires during long download | Low | Medium | Refresh automatically on any API call; if refresh fails, fail task with "reconnect" error |
| Disk fills mid-download | Medium | High | Pre-check free space vs estimated size (duration × bitrate); abort early if <20% free |
| Desktop app cant capture OAuth callback | Medium | Medium | Use manual copy-paste fallback: desktop shows "Paste authorization code:" field |
| spotdl hangs indefinitely on network error | Medium | High | Per-track timeout (300s); overall timeout (1 hour); kill on timeout |
| Cross-platform path separators | Low | Low | Use `pathlib.Path` everywhere; only support macOS for v2.1 |

---

## 📊 Effort Estimate (Remaining Phases)

| Phase | Tasks | Est. Hours | Cumulative |
|-------|-------|------------|------------|
| 3 | Playlist service (2 functions + 2 routes + tests) | 2-4h | 2-4h |
| 4 | spotdl orchestration (subprocess + parsing + routes) | 6-12h | 8-16h |
| 5 | Organize bridge (hook into spotdl completion) | 2-4h | 10-20h |
| 6 | Desktop app (Tauri/Electron UI) | 8-16h | 18-36h |
| 7 | Validation & hardening | 4-8h | 22-44h |

**Total**: ~22-44 hours of development time (spread across multiple sessions).

---

## 🎯 Phase 3 "Very Next Task" Checklist

Start here right now:

- [ ] **Before coding**: Commit any uncommitted work (we're clean on main, but double-check)
- [ ] **Create branch**: `git checkout -b feature/spotify-v2.1-phases-3-7`
- [ ] **Push branch**: `git push -u origin feature/spotify-v2.1-phases-3-7`
- [ ] **Implement `spotify_service.py`** with:
  - [ ] `get_available_playlists(limit=50)` — full implementation
  - [ ] `get_playlist_tracks(playlist_id, limit=100)` — full implementation
  - [ ] Proper error handling (401 → refresh, 429 → retry later, 5xx → propagate)
- [ ] **Update routes**:
  - [ ] `GET /api/v1/spotify/playlists`
  - [ ] `GET /api/v1/spotify/playlist/{playlist_id}/tracks`
- [ ] **Write tests**:
  - [ ] `tests/test_spotify_service.py` (~15 tests)
  - [ ] `tests/test_spotify_routes.py` (~8 tests)
- [ ] **Run full suite**: All 195+ tests must pass
- [ ] **Commit Phase 3**: `git add`, `git commit -m "feat: Spotify playlist service (Phase 3)"`, `git push`
- [ ] **Update `.SESSION_HANDOFF.md`** with Phase 3 summary
- [ ] **Update `docs/design.md`** if any schema changes
- [ ] **Mark Phase 3 complete** in task tracker

---

## 📝 Notes

- **Branching**: Keep work on `feature/spotify-v2.1-phases-3-7` until all backend phases (3-5) complete, then merge to `main` before starting desktop app work (Phase 6). This keeps PRs reviewable.
- **Testing discipline**: Write tests first (TDD style) or immediately after implementation. Never commit without passing tests.
- **API contract**: Keep Spotify API response shapes stable. If Spotify changes fields, handle gracefully with defaults in model.
- **Logging**: Add `logger.info()` at entry/exit of each service function; `logger.error()` on failures.
- **Documentation**: Keep this file updated as phases complete.

---

**Ready to execute Phase 3 following this plan?**
