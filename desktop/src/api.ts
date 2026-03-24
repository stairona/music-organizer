import type {
  OAuthLoginResponse,
  SpotifyPlaylist,
  SpotifyTrack,
  DownloadTask,
  AuthStatus,
} from './types';

const API_BASE = 'http://localhost:8000/api/v1';

async function fetchJson(
  input: RequestInfo,
  init?: RequestInit
): Promise<any> {
  const response = await fetch(input, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...init?.headers,
    },
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`HTTP ${response.status}: ${text}`);
  }

  return response.json();
}

// Auth endpoints
export async function getAuthLoginUrl(): Promise<OAuthLoginResponse> {
  const res = await fetchJson(`${API_BASE}/auth/spotify/login`);
  return res;
}

export async function exchangeAuthCode(
  code: string,
  codeVerifier: string
): Promise<{ success: boolean; access_token?: string }> {
  return fetchJson(`${API_BASE}/auth/spotify/callback`, {
    method: 'POST',
    body: JSON.stringify({ code, code_verifier: codeVerifier }),
  });
}

export async function getAuthStatus(): Promise<AuthStatus> {
  return fetchJson(`${API_BASE}/auth/spotify/status`);
}

// Spotify endpoints
export async function getPlaylists(): Promise<SpotifyPlaylist[]> {
  return fetchJson(`${API_BASE}/spotify/playlists`);
}

export async function getPlaylistTracks(
  playlistId: string
): Promise<SpotifyTrack[]> {
  return fetchJson(`${API_BASE}/spotify/playlist/${playlistId}/tracks`);
}

// Download endpoints
export interface CreateDownloadRequest {
  playlist_id: string;
  destination: string;
  auto_organize?: boolean;
}

export interface CreateDownloadResponse {
  task_id: string;
  status: string;
}

export async function createDownload(
  payload: CreateDownloadRequest
): Promise<CreateDownloadResponse> {
  return fetchJson(`${API_BASE}/downloads`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function getDownloadStatus(
  taskId: string
): Promise<DownloadTask> {
  return fetchJson(`${API_BASE}/downloads/${taskId}/status`);
}

export async function cancelDownload(taskId: string): Promise<{ cancelled: boolean }> {
  return fetchJson(`${API_BASE}/downloads/${taskId}/cancel`, {
    method: 'POST',
  });
}

export async function listDownloads(
  limit: number = 50,
  status?: string
): Promise<DownloadTask[]> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (status) params.append('status', status);
  return fetchJson(`${API_BASE}/downloads?${params.toString()}`);
}

// Health check
export async function healthCheck(): Promise<{ status: string; service?: string }> {
  return fetchJson('http://localhost:8000/health');
}
