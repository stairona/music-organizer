import { useState, useEffect } from 'react';
import { useApp } from '../store';
import { getPlaylists, getPlaylistTracks, createDownload } from '../api';
import { Spinner, ErrorAlert } from '../components';
import type { SpotifyPlaylist } from '../types';
import './Playlists.css';

export function Playlists() {
  const { isAuthenticated } = useApp();
  const [playlists, setPlaylists] = useState<SpotifyPlaylist[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [destination, setDestination] = useState('');
  const [autoOrganize, setAutoOrganize] = useState(true);
  const [downloading, setDownloading] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);

  useEffect(() => {
    if (isAuthenticated) {
      loadPlaylists();
    }
  }, [isAuthenticated]);

  const loadPlaylists = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getPlaylists();
      setPlaylists(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load playlists');
    } finally {
      setLoading(false);
    }
  };

  const toggleSelect = (id: string) => {
    const newSet = new Set(selectedIds);
    if (newSet.has(id)) {
      newSet.delete(id);
    } else {
      newSet.add(id);
    }
    setSelectedIds(newSet);
  };

  const selectAll = () => {
    if (selectedIds.size === playlists.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(playlists.map((p) => p.id)));
    }
  };

  const startDownload = async () => {
    if (selectedIds.size === 0) {
      setDownloadError('Select at least one playlist');
      return;
    }
    if (!destination.trim()) {
      setDownloadError('Please choose a destination folder');
      return;
    }

    setDownloading(true);
    setDownloadError(null);

    try {
      for (const id of selectedIds) {
        await createDownload({
          playlist_id: id,
          destination: destination.trim(),
          auto_organize: autoOrganize,
        });
      }
      // Success - go to downloads page
      window.location.href = '/downloads';
    } catch (err: any) {
      setDownloadError(err.message || 'Failed to start download');
    } finally {
      setDownloading(false);
    }
  };

  const pickDestination = async () => {
    try {
      // Tauri API to open folder picker
      // @ts-ignore
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
        // Fallback: prompt for dev mode
        const path = prompt('Enter destination path:', destination);
        if (path) setDestination(path);
      }
    } catch (err) {
      console.error('Folder picker error:', err);
    }
  };

  if (!isAuthenticated) {
    return <div className="playlists">Please log in first.</div>;
  }

  if (loading) {
    return <div className="center"><Spinner /></div>;
  }

  if (error) {
    return <ErrorAlert message={error} onDismiss={() => setError(null)} />;
  }

  return (
    <div className="playlists">
      <h1>Your Playlists</h1>

      <div className="playlists-controls">
        <button onClick={selectAll} className="btn-small">
          {selectedIds.size === playlists.length ? 'Deselect All' : 'Select All'}
        </button>
        <span className="selected-count">{selectedIds.size} selected</span>
      </div>

      <div className="playlist-list">
        {playlists.map((pl) => (
          <div
            key={pl.id}
            className={`playlist-item ${selectedIds.has(pl.id) ? 'selected' : ''}`}
            onClick={() => toggleSelect(pl.id)}
          >
            <input
              type="checkbox"
              checked={selectedIds.has(pl.id)}
              readOnly
            />
            <div className="playlist-info">
              <div className="playlist-name">{pl.name}</div>
              <div className="playlist-meta">
                {pl.owner} • {pl.track_count} tracks
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="download-panel">
        <h3>Download Selected</h3>

        {downloadError && (
          <ErrorAlert message={downloadError} onDismiss={() => setDownloadError(null)} />
        )}

        <div className="form-group">
          <label>Destination Folder:</label>
          <div className="destination-input">
            <input
              type="text"
              value={destination}
              onChange={(e) => setDestination(e.target.value)}
              placeholder="/path/to/music"
              readOnly
            />
            <button onClick={pickDestination} type="button">
              Browse...
            </button>
          </div>
        </div>

        <div className="form-group">
          <label>
            <input
              type="checkbox"
              checked={autoOrganize}
              onChange={(e) => setAutoOrganize(e.target.checked)}
            />
            Auto-organize after download (by genre)
          </label>
        </div>

        <button
          onClick={startDownload}
          disabled={downloading || selectedIds.size === 0 || !destination}
          className="btn-primary large"
        >
          {downloading ? <Spinner size="small" /> : `Download ${selectedIds.size} Playlist${selectedIds.size > 1 ? 's' : ''}`}
        </button>
      </div>
    </div>
  );
}
