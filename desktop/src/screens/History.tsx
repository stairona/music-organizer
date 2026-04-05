import { useState, useEffect } from 'react';
import { listDownloads } from '../api';
import { Spinner } from '../components';
import type { DownloadTask } from '../types';
import './History.css';

export function History() {
  const [tasks, setTasks] = useState<DownloadTask[]>([]);
  const [loading, setLoading] = useState(true);

  const loadHistory = async () => {
    setLoading(true);
    try {
      const data = await listDownloads(100);
      setTasks(data);
    } catch (err) {
      console.error('Failed to load history:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadHistory();
  }, []);

  if (loading) {
    return <div className="center"><Spinner /></div>;
  }

  return (
    <div className="history">
      <h1>Download History</h1>
      <button onClick={loadHistory} className="btn-refresh">Refresh</button>

      {tasks.length === 0 ? (
        <p className="empty">No downloads yet.</p>
      ) : (
        <table className="history-table">
          <thead>
            <tr>
              <th>Date</th>
              <th>Playlist</th>
              <th>Status</th>
              <th>Tracks</th>
              <th>Destination</th>
            </tr>
          </thead>
          <tbody>
            {tasks.map((task) => (
              <tr key={task.task_id}>
                <td>{new Date(task.created_at * 1000).toLocaleDateString()}</td>
                <td>{task.playlist_name}</td>
                <td><span className={`status status-${task.status}`}>{task.status}</span></td>
                <td>{task.completed_tracks}/{task.total_tracks}</td>
                <td className="dest">{task.destination}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
