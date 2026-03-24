// API Response Types

export interface OAuthLoginResponse {
  auth_url: string;
  state: string;
  code_verifier: string;
}

export interface SpotifyPlaylist {
  id: string;
  name: string;
  owner: string;
  track_count: number;
  snapshot_id?: string;
}

export interface SpotifyTrack {
  id: string;
  name: string;
  artist: string;
  album: string;
  duration_ms: number;
  track_number?: number;
  disc_number?: number;
  isrc?: string;
}

export interface DownloadTask {
  task_id: string;
  playlist_id: string;
  playlist_name: string;
  destination: string;
  status: 'queued' | 'downloading' | 'completed' | 'failed' | 'cancelled';
  progress_percent: number;
  current_track?: string;
  total_tracks: number;
  completed_tracks: number;
  auto_organize: boolean;
  spotdl_pid?: number;
  error_message?: string;
  started_at?: number;
  finished_at?: number;
  created_at: number;
  progress_history?: ProgressSnapshot[];
}

export interface ProgressSnapshot {
  id?: number;
  task_id: string;
  timestamp: number;
  percent: number;
  current_track: string;
  completed_tracks: number;
  total_tracks: number;
  errors?: string[];
}

export interface AuthStatus {
  connected: boolean;
}
