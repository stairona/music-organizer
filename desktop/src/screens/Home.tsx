import { Link } from 'react-router-dom';
import { useApp } from '../store';
import { DownloadIcon, OrganizeIcon, ChartIcon } from '../components/Icons';
import './Home.css';

export function Home() {
  const { activeTasks } = useApp();

  const activeDownloads = activeTasks.filter(
    (t) => t.status === 'downloading' || t.status === 'queued'
  );

  return (
    <div className="home">
      <h1>Welcome to Music Organizer</h1>
      <p className="subtitle">Download and organize your Spotify playlists</p>

      <div className="card">
        <h2>Get Started</h2>
        <p>Paste a Spotify playlist link to start downloading.</p>
        <div className="quick-actions">
          <Link to="/download" className="btn-primary">
            Download Music
          </Link>
          <Link to="/organize" className="btn-secondary">
            Organize Library
          </Link>
          <Link to="/downloads" className="btn-secondary">
            Active Downloads ({activeDownloads.length})
          </Link>
        </div>
      </div>

      <div className="features">
        <div className="feature">
          <DownloadIcon className="feature-icon" />
          <h3>Download</h3>
          <p>Paste a Spotify playlist URL and download via spotdl</p>
        </div>
        <div className="feature">
          <OrganizeIcon className="feature-icon" />
          <h3>Organize</h3>
          <p>Sort your music library by genre</p>
        </div>
        <div className="feature">
          <ChartIcon className="feature-icon" />
          <h3>Track</h3>
          <p>Monitor download progress in real-time</p>
        </div>
      </div>
    </div>
  );
}
