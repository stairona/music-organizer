import type { DownloadTask } from '../types';
import './StatusBadge.css';

export function StatusBadge({ status }: { status: DownloadTask['status'] }) {
  return (
    <span className={`status-badge status-${status}`}>
      {status}
    </span>
  );
}
