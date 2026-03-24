# Phase 6 Detailed Implementation Plan — Desktop App (Tauri + React)

**Branch**: `feature/spotify-v2.1-phases-4-7`
**Target**: Complete desktop wrapper for the FastAPI backend
**Tech Stack**:
- **Desktop Runtime**: Tauri (Rust + WebView)
- **Frontend**: React 18 + TypeScript + Vite
- **Styling**: Tailwind CSS (or plain CSS for simplicity)
- **API**: REST over `http://localhost:8000` (backend runs separate process)
- **Authentication OAuth Flow**: System browser → localhost callback server

**Duration Estimate**: 8-16 hours (depending on experience with Tauri/React)
**Prerequisites**:
- Rust toolchain installed (`rustup`, `cargo`)
- Node.js 18+
- Tauri CLI: `npm install -g @tauri-apps/cli`
- Backend running and tested (`uvicorn app.backend.main:app --reload`)

---

## 📋 Phase 6 Overview

**Goal**: Build a native desktop application that provides a user-friendly interface to the existing FastAPI backend.

**Architecture**:
```
┌─────────────────────────────────────────────────────────────┐
│                    Tauri Desktop App                       │
│  ┌─────────────────┐  ┌─────────────────┐                 │
│  │      Rust       │  │     React       │                 │
│  │  (main.rs)      │◄─►│  (src/App.tsx)  │                 │
│  │  - HTTP client  │  │  - UI state     │                 │
│  │  - Backend spawn│  │  - Components   │                 │
│  │  - Localhost    │  │  - Polling      │                 │
│  │    HTTP server  │  │                 │                 │
│  └─────────────────┘  └─────────────────┘                 │
└─────────────────────┬──────────────────────────────────────┘
                      │ HTTP/REST (localhost:8000)
                      ▼
          ┌─────────────────────────┐
          │   FastAPI Backend       │
          │   (music-organizer)     │
          └─────────────────────────┘
```

---

## ✅ Pre-Phase 6 Checklist

Before starting Phase 6, ensure:

- [x] **Backend API fully functional** (all endpoints respond correctly)
  - `GET /health` → `{"status": "ok"}`
  - `GET /api/v1/auth/spotify/login` → returns auth URL
  - `POST /api/v1/auth/spotify/callback` → exchanges code
  - `GET /api/v1/auth/spotify/status` → connection status
  - `GET /api/v1/spotify/playlists` → list playlists
  - `GET /api/v1/spotify/playlist/{id}/tracks` → track list
  - `POST /api/v1/downloads` → creates task, starts background download
  - `GET /api/v1/downloads/{id}/status` → status + progress
  - `POST /api/v1/downloads/{id}/cancel` → cancels
- [x] **232 unit tests passing** (including async route tests)
- [x] **Local verification script passes** (`local_smoke_test.py`)
- [x] **Spotipy and spotdl installed** (for manual testing):
  ```bash
  pip install spotipy spotdl
  ```
- [x] **Spotify developer app created** (to get Client ID)
  - Redirect URI: `http://localhost:8080/callback` (or custom protocol)
- [x] **Branch up to date on GitHub**: `feature/spotify-v2.1-phases-4-7`
- [x] **Session handoff updated**: `.SESSION_HANDOFF.md`

---

### Recommended Quick Manual Test (5 min)

```bash
# Terminal 1: Start backend
cd music-organizer
uvicorn app.backend.main:app --reload

# Terminal 2: Test with curl (or use /docs API browser at http://localhost:8000/docs)
curl http://localhost:8000/health
# Should return: {"status":"ok","service":"music-organizer-api"}

# Test playlist fetch (will fail without auth but should return 401 or 500):
curl -X POST "http://localhost:8000/api/v1/downloads" \
  -H "Content-Type: application/json" \
  -d '{"playlist_id":"test","destination":"/tmp"}'
# Should return 401 (not authenticated)
```

If this works, backend is ready for desktop app.

---

## 🏗️ Phase 6 Implementation Steps

### Step 6.1: Decision Record (5 min)

**Decision**: Tauri + React + TypeScript + Vite + Tailwind CSS (or plain)

**Rationale**:
- Tauri: small bundle, native performance, secure, modern
- React: widely known, component ecosystem, good TypeScript support
- Vite: fast dev server, Tauri plugin available
- Tailwind: rapid styling (optional)

**Alternatives considered**:
- Electron: heavier but zero Rust knowledge needed. Rejected for bundle size.
- Vue: fine but React more common.
- Svelte: great but smaller ecosystem.

---

### Step 6.2: Initialize Tauri + React Project (15 min)

```bash
# From project root (music-organizer/)
cd /Users/nicolasaguirre/zprojects/music-organizer

# Create desktop directory
mkdir -p desktop
cd desktop

# Initialize Tauri app with React + TypeScript template
# Using npm create command
npm create tauri-app@latest . -- --template react-ts

# Answer prompts:
# - Project name: music-organizer-desktop
# - Choose package manager: npm (or yarn/pnpm)
# - Install deps automatically? Yes

# This creates:
# desktop/
#   src/          # React app
#   src-tauri/    # Rust backend
#   package.json
#   tauri.conf.json
```

**If you prefer Electron**, do:
```bash
mkdir desktop && cd desktop
npm init -y
npm install electron electron-builder react react-dom
# Manually set up main.js, index.html, build config
```

But we'll proceed with Tauri.

---

### Step 6.3: Configure Tauri App (10 min)

Update `desktop/tauri.conf.json`:

```json
{
  "build": {
    "beforeDevCommand": "npm run dev",
    "beforeBuildCommand": "npm run build",
    "devPath": "http://localhost:1420",  // Vite dev server
    "distDir": "../dist"  // React build output
  },
  "package": {
    "productName": "Music Organizer",
    "version": "2.1.0"
  },
  "tauri": {
    "application": {
      "windows": [
        {
          "title": "Music Organizer",
          "width": 1200,
          "height": 800,
          "resizable": true
        }
      ]
    },
    "security": {
      "csp": "default-src 'self'; connect-src http://localhost:*"  // Allow localhost API
    }
  }
}
```

Also configure CORS in backend to accept Tauri origin:

In `app/backend/main.py`, add:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["tauri://localhost", "http://localhost:1420"],  # Tauri dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

### Step 6.4: Design UI Component Structure (15 min)

**Screens**:

1. **LoginScreen** (`/login`)
   - If not authenticated: show "Connect to Spotify" button
   - Button opens system browser to `/auth/spotify/login`
   - After auth, backend redirects to `http://localhost:8080/callback?code=...`
   - App opens localhost server to catch callback, then POSTs code to backend
   - On success: navigate to PlaylistScreen

2. **PlaylistScreen** (`/playlists`)
   - Table: playlist name, owner, track count, checkbox
   - "Download" button → start download for selected playlists
   - Destination folder picker (using Tauri dialog)
   - "Auto-organize" toggle (default ON)
   - Shows active downloads in progress bar at bottom

3. **DownloadsScreen** (`/downloads`)
   - List of active/completed/failed/cancelled tasks
   - Sort by date, filter by status
   - Each item: progress bar (if downloading), cancel button (if running)
   - Click to see details (task ID, destination, timestamps)

4. **HistoryScreen** (`/history`)
   - Read-only list of all past downloads (from `list_download_tasks()`)
   - Shows status, date, playlist name

**Shared Components**:
- `Navbar`: navigation links (Playlists, Downloads, History, Logout)
- `Spinner`: loading indicator
- `ProgressBar`: animated progress
- `StatusBadge`: color-coded status (queued/downloading/completed/failed/cancelled)
- `ErrorAlert`: display errors

**State Management**:
- React Context or Zustand for global state (auth token, current screen, active tasks)
- Each screen can fetch its own data, or we poll the backend every 2-3s for active tasks

---

### Step 6.5: Implement Backend Spawn + Health Check (20 min)

**Problem**: The desktop app needs to ensure backend is running before making requests.

**Solution**: On app startup, Tauri Rust command spawns `uvicorn app.backend.main:app --host 127.0.0.1 --port 8000` as child process.

In `desktop/src-tauri/src/main.rs`:

```rust
#[tauri::command]
async fn start_backend() -> Result<String, String> {
    use std::process::{Command, Stdio};
    use std::io;

    // Check if already running on port 8000
    // If not, spawn
    let output = Command::new("python")
        .args(["-m", "uvicorn", "app.backend.main:app", "--host", "127.0.0.1", "--port", "8000"])
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .spawn()
        .map_err(|e| e.to_string())?;

    // Store output PID in app state for later termination
    // ...
    Ok("Backend started".to_string())
}
```

Also add `stop_backend()` command to kill the child process on app exit.

**Simpler Alternative**: Just require user to run backend separately in a terminal. Document this in README. For MVP, let's do that — less complexity.

---

### Step 6.6: Implement OAuth Flow with Localhost Callback (30 min)

This is the trickiest part. Here's the flow:

1. User clicks "Connect Spotify"
2. Desktop app calls `GET /api/v1/auth/spotify/login` via fetch
3. Backend returns `{auth_url, state, code_verifier}`
4. Desktop opens system browser to `auth_url` (using Tauri's `open` command)
5. User logs in, authorizes
6. Spotify redirects to `http://localhost:8080/callback?code=...&state=...`
7. **Desktop app must be listening on port 8080** to catch this redirect
8. Desktop extracts `code` and `code_verifier` (stored from step 3)
9. Desktop POSTs to backend `/api/v1/auth/spotify/callback` with `{code, code_verifier}`
10. Backend returns tokens; desktop stores connection status

**Implementation**:

- Tauri: Use `tiny-http` or `warp` to run a tiny HTTP server on localhost:8080 that listens for the `/callback` route.
- Simpler: Instead of localhost server, use **custom protocol** `music-organizer://callback` and register it with Tauri. Then backend redirects to `music-organizer://callback?code=...`. Desktop receives via Tauri deep link event.
- **Simplest for MVP**: **Manual copy-paste**. After user authorizes in browser, Spotify shows "Copy this code". User pastes code into desktop app. App then POSTs to callback. No local server needed.

**Recommendation**: Start with manual copy-paste for speed. Can upgrade to localhost server later.

**Manual flow**:
1. Desktop: `fetch('/api/v1/auth/spotify/login')` → get `auth_url`
2. Desktop: `open(auth_url)` in system browser
3. User authorizes; browser shows code
4. User pastes code into desktop text field + clicks "Confirm"
5. Desktop: `fetch('/api/v1/auth/spotify/callback', {method: 'POST', body: {code, code_verifier}})`
6. On success: set auth state, navigate to playlists

---

### Step 6.7: Implement Playlist Fetching (20 min)

Screen: `/playlists`

- On mount, fetch `GET /api/v1/spotify/playlists`
- Store in state (list of `{id, name, owner, track_count}`)
- Render table with checkboxes
- "Download" button enabled when at least one selected
- Destination picker: Tauri's `dialog` API to choose folder
- Auto-organize toggle (boolean)

When Download clicked:
- POST `/api/v1/downloads` with `{playlist_id, destination, auto_organize}`
- Returns `{task_id, status}`
- Add task to local active tasks state
- Navigate to `/downloads` to show progress

---

### Step 6.8: Implement Downloads Polling (15 min)

Screen: `/downloads`

- On mount, start polling every 2 seconds:
  ```ts
  useEffect(() => {
    const interval = setInterval(async () => {
      for (const task of activeTasks) {
        const res = await fetch(`/api/v1/downloads/${task.id}/status`);
        const data = await res.json();
        updateTask(task.id, data);
      }
    }, 2000);
    return () => clearInterval(interval);
  }, [activeTasks]);
  ```
- Show progress bars (width = `progress_percent%`)
- Show current track name under each bar
- Cancel button: `POST /api/v1/downloads/{id}/cancel` (active only when status=downloading)

---

### Step 6.9: Implement History Screen (10 min)

Screen: `/history`

- On mount, call `list_download_tasks(limit=50)` from store (need new API endpoint)
  - Wait, we don't have list endpoint for all tasks! We need to add it.
- **Add new route**: `GET /api/v1/downloads` → returns list of tasks (maybe with status filter)
  - Implement in `routes/__init__.py`
  - `def list_downloads(limit: int = 50, status: Optional[str] = None)`
  - Uses `store.list_download_tasks()`
- Render as table: Date, Playlist, Status, Tracks, Destination

---

### Step 6.10: Navigation & State Management (15 min)

Use React Router (or Tauri's navigation):

```tsx
// App.tsx
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom';

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  return (
    <BrowserRouter>
      <Navbar />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/login" element={<Login />} />
        <Route path="/playlists" element={<Playlists />} />
        <Route path="/downloads" element={<Downloads />} />
        <Route path="/history" element={<History />} />
      </Routes>
    </BrowserRouter>
  );
}
```

Global state: Use Context API or Zustand to store:
- `authToken` (boolean, or actual token if needed)
- `activeTasks` array
- `backendRunning` boolean

---

### Step 6.11: Error Handling & UX Polish (20 min)

- Show error toasts (use `react-toastify` or Tauri notifications)
- Handle backend unreachable (show "Start Backend" button or instruction)
- Handle Spotify auth errors (show "Reconnect")
- Confirm dialogs for cancellations
- Auto-refresh on reconnect

---

### Step 6.12: Packaging & Distribution (15 min)

Build Tauri app:

```bash
cd desktop
npm run tauri build
# Output: src-tauri/target/release/bundle/macos/Music Organizer_2.1.0.dmg
```

Test DMG on your Mac:
- Copy to /Applications
- Run; should open window
- Backend not included; user must run `uvicorn` separately (for MVP) OR
- Bundle Python + dependencies? Complex. For now, document: "Start backend separately"

**For self-use**: you can run backend manually. For distribution, you'd need to package the Python backend with PyInstaller or similar. That's a future enhancement.

---

## 📁 New Files/Directories to Create

```
desktop/
├── src/
│   ├── components/
│   │   ├── Navbar.tsx
│   │   ├── Spinner.tsx
│   │   ├── ProgressBar.tsx
│   │   ├── StatusBadge.tsx
│   │   └── ErrorAlert.tsx
│   ├── screens/
│   │   ├── Login.tsx
│   │   ├── Playlists.tsx
│   │   ├── Downloads.tsx
│   │   ├── History.tsx
│   │   └── Home.tsx
│   ├── api.ts           # fetch wrapper for localhost:8000
│   ├── store.ts         # global state (React Context / Zustand)
│   ├──types.ts          # TypeScript interfaces
│   ├── App.tsx
│   └── main.tsx
├── src-tauri/
│   ├── src/
│   │   └── main.rs      # commands for open, dialog, spawn backend?
│   ├── Cargo.toml
│   └── tauri.conf.json  (generated)
├── package.json
├── tsconfig.json
├── vite.config.ts
├── tailwind.config.js (if using)
└── tauri.conf.json
```

---

## 🧪 Phase 6 Testing Strategy

- **Unit tests**: Not much; React components are mostly presentational
- **Manual testing**:
  1. Start backend (`uvicorn app.backend.main:app --reload`)
  2. Launch desktop app (`npm run tauri dev`)
  3. Click Connect → authorize in browser → confirm connection
  4. View playlists; select one; set destination; download
  5. Watch progress bar advance; try cancel
  6. Check files appear in destination and get organized
  7. View History screen

- **Test scenarios**:
  - No backend running: should show error
  - Auth expired: should prompt re-login
  - Download fails (spotdl error): should show failed status
  - Large playlist (100+ tracks): progress updates smoothly
  - Cancel mid-download: task becomes cancelled, spotdl terminates

---

## 🐛 Known Issues & Mitigations

| Issue | Mitigation |
|-------|------------|
| Backend not started by app | Document: "Start backend manually"; optionally add "Start Backend" button that spawns uvicorn via Tauri command |
| Spotify token refresh fails | Backend auto-refresh should work; if refresh fails, show "Reconnect Spotify" |
| spotdl not installed | Check at startup: run `spotdl --version`; show error if missing |
| Disk full during download | No pre-check yet; Phase 7 will add |
| CORS errors | Ensure backend allows `tauri://localhost` or `http://localhost:1420` |
| Localhost callback complexity | Use manual copy-paste for MVP; implement localhost server later |

---

## 🔄 Phase 6 → Phase 7 Transition Criteria

Phase 6 is **complete** when:

- [ ] Desktop app builds successfully (`npm run tauri build`)
- [ ] All screens implemented and navigable
- [ ] OAuth flow works (manual copy-paste)
- [ ] Playlist fetch → download → progress display works
- [ ] Cancel button kills spotdl process
- [ ] History screen shows past downloads
- [ ] Manual end-to-end test passes: download 3-track playlist → files organized into genre folders

Once Phase 6 complete, move to Phase 7:
- Add integration tests (mock full flow)
- Add error handling enhancements
- Add logging
- Add disk space check
- Polish UI

---

## 📝 Quick Reference: API Endpoints to Use

| Endpoint | Method | Purpose | Auth Required |
|----------|--------|---------|---------------|
| `/health` | GET | Health check | No |
| `/api/v1/auth/spotify/login` | GET | Get auth URL | No |
| `/api/v1/auth/spotify/callback` | POST | Exchange code | No |
| `/api/v1/auth/spotify/status` | GET | Check connection | No |
| `/api/v1/spotify/playlists` | GET | List playlists | **Yes** |
| `/api/v1/spotify/playlist/{id}/tracks` | GET | List tracks | **Yes** |
| `/api/v1/downloads` | POST | Start download | **Yes** |
| `/api/v1/downloads/{id}/status` | GET | Get task status | **Yes** |
| `/api/v1/downloads/{id}/cancel` | POST | Cancel task | **Yes** |
| `GET /api/v1/downloads` | GET | List tasks (new) | **Yes** *(to add)* |

**Note**: We need to add `GET /api/v1/downloads` (list endpoint) before History screen works. This is a small addition to `routes/__init__.py`.

---

## ⚡ Pre-Implementation Checklist

- [ ] Create `desktop/` directory (will be gitignored? No, commit it)
- [ ] Initialize Tauri app with `npm create tauri-app@latest`
- [ ] Update `tauri.conf.json` CORS and build config
- [ ] Add CORSMiddleware to FastAPI (allow Tauri origin)
- [ ] Install React dependencies: `react-router-dom`, optional: `zustand`, `react-toastify`, `tailwind`
- [ ] Plan component file structure
- [ ] Decide on API wrapper architecture (fetch with base URL)
- [ ] Consider TypeScript types for all API responses

---

## 🎯 First Development Session (Session 1 of ~4)

**Goal**: Have Tauri app running with navigation and Login screen.

**Tasks**:
1. Initialize Tauri + React + TS
2. Configure CORS in backend
3. Create basic navigation (Navbar with 4 routes)
4. Implement Login screen with manual code paste flow
5. Test auth flow end-to-end (backend + browser + desktop)

When this is done, commit: "feat(desktop): initial Tauri app with login screen"

---

**Ready to begin?** Let me know if you want me to start implementing Phase 6 now, or if you have questions about the plan. I can also add the missing `GET /api/v1/downloads` endpoint to the backend first if you'd like.
