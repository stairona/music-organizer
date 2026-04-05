import type {
  DownloadTask,
  OrganizeResult,
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

// None needed

// Download endpoints
export interface CreateDownloadRequest {
  playlist_url: string;  // Spotify playlist URL or ID
  destination: string;
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

// Organize endpoint
export interface OrganizeRequest {
  source: string;
  destination?: string;
  mode?: 'copy' | 'move';
  level?: string;
  profile?: string;
  dry_run?: boolean;
  skip_existing?: boolean;
  skip_unknown_only?: boolean;
  on_collision?: string;
  limit?: number;
  exclude_dir?: string[];
}

export async function organizeFiles(
  payload: OrganizeRequest
): Promise<OrganizeResult> {
  return fetchJson(`${API_BASE}/organize`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

// Health check
export async function healthCheck(): Promise<{ status: string; service?: string }> {
  return fetchJson('http://localhost:8000/health');
}
