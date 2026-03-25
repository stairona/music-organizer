# Music Organizer Desktop (Tauri + React)

Desktop UI for the Music Organizer backend.

## Prerequisites

- Node.js 18+
- Rust toolchain (rustup, cargo)
- Tauri CLI: `npm install -g @tauri-apps/cli`
- Python backend dependencies (see root `README.md`)

## Setup

1. **Install dependencies**:
   ```bash
   npm install
   ```

2. **Start backend** (in another terminal, from project root):
   ```bash
   cd ..
   uvicorn app.backend.main:app --reload --host 127.0.0.1 --port 8000
   ```

3. **Configure Spotify**:
   - Create a Spotify app at https://developer.spotify.com/dashboard
   - Set redirect URI (if using localhost callback method): `http://localhost:8080/callback`
   - Set environment variable:
     ```bash
     export SPOTIPY_CLIENT_ID="your-client-id"
     ```
   - Install spotdl: `pip install spotdl`

4. **Run in development**:
   ```bash
   npm run tauri dev
   ```

5. **Build for production**:
   ```bash
   npm run tauri build
   ```
   Output will be in `src-tauri/target/release/bundle/`.

## Usage

- **Login**: Click "Connect Spotify", open the URL in browser, paste the code.
- **Playlists**: Browse your Spotify playlists, select ones to download.
- **Downloads**: Watch progress, cancel if needed.
- **History**: View past downloads.

## Screens

- `/` - Home dashboard
- `/login` - Spotify authentication
- `/playlists` - Select playlists to download
- `/downloads` - Active and recent downloads
- `/history` - Complete download history

## Troubleshooting

- **Backend not reachable**: Ensure backend is running on http://localhost:8000
- **CORS errors**: Backend CORS configured for `http://localhost:1420` (dev) and `tauri://localhost` (prod)
- **Spotify auth fails**: Check `SPOTIPY_CLIENT_ID` is set and redirect URI matches.
- **Port already in use**: Change ports in `vite.config.ts` or backend command.

## Tech Stack

- Tauri (Rust + WebView)
- React 18 + TypeScript
- Vite
- Tailwind-less (plain CSS)
