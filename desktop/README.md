# Music Organizer Desktop (Tauri + React)

Simplified desktop UI for downloading and organizing Spotify playlists via spotdl.

## Prerequisites

- Node.js 18+
- Rust toolchain (rustup, cargo)
- Tauri CLI: `npm install -g @tauri-apps/cli`
- Python backend with spotdl installed (`pip install spotdl`)

## Setup

1. **Install dependencies**:
   ```bash
   npm install
   ```

2. **Start backend** (in another terminal, from project root):
   ```bash
   cd ..
   PYTHONPATH=src uvicorn app.backend.main:app --reload --host 127.0.0.1 --port 8000
   ```

3. **Run in development**:
   ```bash
   npm run tauri dev
   ```

4. **Build for production**:
   ```bash
   npm run tauri build
   ```
   Output will be in `src-tauri/target/release/bundle/`.

## Usage (No Login Required!)

1. **Download** (`/download`):
   - Paste a Spotify playlist URL (e.g., `https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M`)
   - Choose destination folder
   - Click **Start Download**
   - Watch progress on **Active** page

2. **Organize** (`/organize`):
   - After download completes, select the source folder (where files were saved)
   - Optionally choose a different destination (leave blank to organize in-place)
   - Pick mode: **Move** (relocates files) or **Copy** (keeps originals)
   - Choose genre level: General (Electronic, Rock) or Specific (House, Techno)
   - Optionally check "Skip existing files" and/or "Dry run" (simulate)
   - Click **Organize**; view summary

3. **Monitor** (`/downloads`):
   - View active downloads with percentage progress
   - Cancel running downloads
   - See completed downloads in the history table

## Screens

- `/` - Home with quick links
- `/download` - Paste Spotify URL to start download
- `/downloads` - Active downloads and history
- `/organize` - Manual library organization
- `/history` - Alternative history view

## Notes

- No Spotify account linking required — spotdl handles access internally.
- Auto-organize after download is **manual only** (intentional).
- Progress shows percentage; total track count may be 0 until spotdl finishes.
- Ensure `spotdl` is in PATH; the backend invokes it as a subprocess.

## Troubleshooting

- **Backend not reachable**: Ensure backend is running on http://localhost:8000 with `PYTHONPATH=src`.
- **CORS errors**: Backend CORS configured for Tauri dev and production.
- **spotdl not found**: Install spotdl globally (`pip install spotdl`) or ensure it's in PATH.
- **Download fails**: Check backend logs for spotdl errors; common issues: invalid playlist URL or network.

## Tech Stack

- Tauri v2 (Rust + WebView)
- React 18 + TypeScript
- Vite
- Plain CSS
