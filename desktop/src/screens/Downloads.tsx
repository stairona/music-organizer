import { useState, useEffect } from 'react';
import { useApp } from '../store';
import { getDownloadStatus, cancelDownload } from '../api';
import { Spinner, ProgressBar, StatusBadge, ErrorAlert } from '../components';
import type { DownloadTask } from '../types';
import './Downloads.css';

export function Downloads() {
  const { activeTasks, updateTask } = useApp();
  const [refreshing, setRefreshing] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const refreshTask = async (taskId: string) => {
    try {
      const status = await getDownloadStatus(taskId);
      updateTask(taskId, status);
    } catch (err: any) {
      setErrors((prev) => ({ ...prev, [taskId]: err.message || 'Failed to fetch status' }));
    }
  };

  const handleCancel = async (taskId: string) => {
    if (!confirm('Cancel this download?')) return;
    try {
      const res = await cancelDownload(taskId);
      if (res.cancelled) {
        updateTask(taskId, { status: 'cancelled', finished_at: Math.floor(Date.now() / 1000) });
      }
    } catch (err: any) {
      setErrors((prev) => ({ ...prev, [taskId]: err.message || 'Failed to cancel' }));
    }
  };

  // Refresh all active tasks periodically
  useEffect(() => {
    const active = activeTasks.filter((t) =>
      t.status === 'downloading' || t.status === 'queued'
    );
    if (active.length === 0) return;

    const interval = setInterval(() => {
      active.forEach((t) => refreshTask(t.task_id));
    }, 2000);
    return () => clearInterval(interval);
  }, [activeTasks]);

  const activeCount = activeTasks.filter((t) =>
    t.status === 'downloading' || t.status === 'queued'
  ).length;

  return (
    <div className="downloads">
      <h1>Downloads</h1>

      {activeCount === 0 ? (
        <div className="empty-state">
          <p>No active downloads.</p>
          <p><a href="/playlists">Go to Playlists</a> to start downloading.</p>
        </div>
      ) : (
        <div className="task-list">
          {activeTasks
            .filter((t) => t.status === 'downloading' || t.status === 'queued')
            .map((task) => (
              <div key={task.task_id} className="task-card">
                <div className="task-header">
                  <h3>{task.playlist_name}</h3>
                  <StatusBadge status={task.status} />
                </div>
                <div className="task-meta">
                  {task.destination}
                </div>

                {errors[task.task_id] && (
                  <ErrorAlert message={errors[task.task_id]} onDismiss={() => {
                    setErrors((prev) => {
                      const next = { ...prev };
                      delete next[task.task_id];
                      return next;
                    });
                  }} />
                )}

                {task.status === 'downloading' && (
                  <>
                    <ProgressBar progress={task.progress_percent} label={task.current_track} />
                    <div className="task-progress-text">
                      {task.completed_tracks} / {task.total_tracks} tracks
                    </div>
                  </>
                )}

                <div className="task-actions">
                  <button
                    onClick={() => handleCancel(task.task_id)}
                    disabled={task.status !== 'downloading'}
                    className="btn-danger"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            ))}
        </div>
      )}

      <h2>History</h2>
      {activeTasks.filter((t) => t.status !== 'downloading' && t.status !== 'queued').length === 0 ? (
        <p className="empty">No completed downloads yet.</p>
      ) : (
        <table className="history-table">
          <thead>
            <tr>
              <th>Playlist</th>
              <th>Status</th>
              <th>Tracks</th>
              <th>Date</th>
            </tr>
          </thead>
          <tbody>
            {activeTasks
              .filter((t) => t.status !== 'downloading' && t.status !== 'queued')
              .map((task) => (
                <tr key={task.task_id}>
                  <td>{task.playlist_name}</td>
                  <td><StatusBadge status={task.status} /></td>
                  <td>{task.completed_tracks}/{task.total_tracks}</td>
                  <td>{task.finished_at ? new Date(task.finished_at * 1000).toLocaleDateString() : '-'}</td>
                </tr>
              ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
