import { Link } from 'react-router-dom';
import { useApp } from '../store';
import './Home.css';

export function Home() {
  const { isAuthenticated, activeTasks } = useApp();

  const activeDownloads = activeTasks.filter(
    (t) => t.status === 'downloading' || t.status === 'queued'
  );

  return (
    <div className="home">
      <h1>Welcome to Music Organizer</h1>
      <p className="subtitle">Download and organize your Spotify playlists</p>

      {!isAuthenticated ? (
        <div className="card">
          <h2>Get Started</h2>
          <p>Connect your Spotify account to browse playlists and download music.</p>
          <Link to="/login" className="btn-primary">
            Connect Spotify
          </Link>
        </div>
      ) : (
        <div className="card">
          <h2>Ready!</h2>
          <p>You're connected to Spotify.</p>
          <div className="quick-actions">
            <Link to="/playlists" className="btn-primary">
              Browse Playlists
            </Link>
            <Link to="/downloads" className="btn-secondary">
              View Downloads ({activeDownloads.length})
            </Link>
          </div>
        </div>
      )}

      <div className="features">
        <div className="feature">
          <span role="img" aria-label="download">⬇️</span>
          <h3>Download</h3>
          <p>Download playlists via spotdl</p>
        </div>
        <div className="feature">
          <span role="img" aria-label="organize">📁</span>
          <h3>Organize</h3>
          <p>Auto-sort by genre using metadata</p>
        </div>
        <div className="feature">
          <span role="img" aria-label="track">📊</span>
          <h3>Track</h3>
          <p>Monitor download progress in real-time</p>
        </div>
      </div>
    </div>
  );
}
