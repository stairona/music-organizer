import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useApp } from '../store';
import { createDownload } from '../api';
import { Spinner, ErrorAlert } from '../components';
import './Download.css';

export function Download() {
  const { addTask } = useApp();
  const navigate = useNavigate();

  const [playlistUrl, setPlaylistUrl] = useState('');
  const [destination, setDestination] = useState('');
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const pickDestination = async () => {
    try {
      // @ts-ignore - Tauri API
      if (window.__TAURI__) {
        // @ts-ignore
        const selected = await window.__TAURI__.dialog.open({
          directory: true,
          multiple: false,
        });
        if (selected && typeof selected === 'string') {
          setDestination(selected);
        }
      } else {
        // Dev fallback
        const path = prompt('Enter destination path:', destination);
        if (path) setDestination(path);
      }
    } catch (err) {
      console.error('Folder picker error:', err);
    }
  };

  const startDownload = async () => {
    if (!playlistUrl.trim()) {
      setError('Please enter a Spotify playlist URL');
      return;
    }
    if (!destination.trim()) {
      setError('Please choose a destination folder');
      return;
    }

    setDownloading(true);
    setError(null);

    try {
      const res = await createDownload({
        playlist_url: playlistUrl.trim(),
        destination: destination.trim(),
      });

      // Add task to local state for immediate feedback
      addTask({
        task_id: res.task_id,
        playlist_id: '', // will be updated by polling
        playlist_name: 'Unknown Playlist',
        destination: destination.trim(),
        status: 'queued',
        progress_percent: 0,
        completed_tracks: 0,
        total_tracks: 0,
        auto_organize: false,
        created_at: Math.floor(Date.now() / 1000),
      });

      // Navigate to downloads page to see progress
      navigate('/downloads');
    } catch (err: any) {
      setError(err.message || 'Failed to start download');
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="download">
      <h1>Download Music</h1>

      <div className="download-card">
        {error && <ErrorAlert message={error} onDismiss={() => setError(null)} />}

        <div className="form-group">
          <label htmlFor="playlist-url">Spotify Playlist URL</label>
          <input
            id="playlist-url"
            type="text"
            value={playlistUrl}
            onChange={(e) => setPlaylistUrl(e.target.value)}
            placeholder="https://open.spotify.com/playlist/..."
            className="url-input"
            disabled={downloading}
            autoComplete="off"
          />
        </div>

        <div className="form-group">
          <label htmlFor="destination">Save to Folder</label>
          <div className="destination-input">
            <input
              id="destination"
              type="text"
              value={destination}
              onChange={(e) => setDestination(e.target.value)}
              placeholder="Select a folder..."
              readOnly
              disabled={downloading}
            />
            <button onClick={pickDestination} type="button" disabled={downloading} className="btn-secondary">
              Browse
            </button>
          </div>
        </div>

        <button
          onClick={startDownload}
          disabled={downloading || !playlistUrl.trim() || !destination.trim()}
          className="btn-primary btn-lg btn-block"
        >
          {downloading ? <Spinner size="small" /> : 'Start Download'}
        </button>
      </div>

      <div className="info">
        <h3>How it works</h3>
        <ul>
          <li>Paste a Spotify playlist URL above.</li>
          <li>Choose where to save the downloaded files.</li>
          <li>Click Start Download and watch progress in real-time.</li>
          <li>After download completes, organize your library by genre.</li>
        </ul>
        <p><strong>Note:</strong> No login required — spotdl handles authentication automatically.</p>
      </div>
    </div>
  );
}
