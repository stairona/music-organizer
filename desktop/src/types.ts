// API Response Types

// Removed Spotify auth and playlist types (no longer used)

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

// Organize result (matches backend OrganizeResult)
export interface OrganizeResult {
  success: boolean;
  summary: {
    total: number;
    processed: number;
    moved_or_copied: number;
    unknown_count: number;
    reason_counts: Record<string, number>;
    specific_counter: Record<string, number>;
    general_counter: Record<string, number>;
    skipped_counts?: Record<string, number>;
  };
  unknown_diagnostics?: {
    count: number;
    sample_paths: string[];
  };
  csv_report_path?: string;
  journal_saved?: boolean;
  warnings?: string[];
}
