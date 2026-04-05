import { useState } from 'react';
import { organizeFiles } from '../api';
import { Spinner, ErrorAlert } from '../components';
import type { OrganizeResult } from '../types';
import './Organize.css';

export function Organize() {
  const [source, setSource] = useState('');
  const [destination, setDestination] = useState('');
  const [mode, setMode] = useState<'copy' | 'move'>('move');
  const [level, setLevel] = useState('general');
  const [profile, setProfile] = useState('default');
  const [skipExisting, setSkipExisting] = useState(false);
  const [dryRun, setDryRun] = useState(false);

  const [organizing, setOrganizing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<OrganizeResult | null>(null);

  const pickSource = async () => {
    try {
      // @ts-ignore
      if (window.__TAURI__) {
        // @ts-ignore
        const selected = await window.__TAURI__.dialog.open({
          directory: true,
          multiple: false,
        });
        if (selected && typeof selected === 'string') {
          setSource(selected);
        }
      } else {
        const path = prompt('Enter source directory:', source);
        if (path) setSource(path);
      }
    } catch (err) {
      console.error('Folder picker error:', err);
    }
  };

  const pickDestination = async () => {
    try {
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
        const path = prompt('Enter destination directory:', destination);
        if (path) setDestination(path);
      }
    } catch (err) {
      console.error('Folder picker error:', err);
    }
  };

  const handleOrganize = async () => {
    if (!source.trim()) {
      setError('Please select a source folder');
      return;
    }

    setOrganizing(true);
    setError(null);
    setResult(null);

    try {
      const payload: any = {
        source: source.trim(),
        mode,
        level,
        profile,
        skip_existing: skipExisting,
        dry_run: dryRun,
      };
      if (destination.trim()) {
        payload.destination = destination.trim();
      }

      const res = await organizeFiles(payload);
      setResult(res);
    } catch (err: any) {
      setError(err.message || 'Organization failed');
    } finally {
      setOrganizing(false);
    }
  };

  return (
    <div className="organize">
      <h1>Organize Music Library</h1>

      <div className="organize-card">
        {error && <ErrorAlert message={error} onDismiss={() => setError(null)} />}

        <div className="form-group">
          <label>Source Folder (music to organize):</label>
          <div className="destination-input">
            <input
              type="text"
              value={source}
              onChange={(e) => setSource(e.target.value)}
              placeholder="/path/to/music"
              readOnly
              disabled={organizing}
            />
            <button onClick={pickSource} type="button" disabled={organizing} className="btn-secondary">
              Browse...
            </button>
          </div>
        </div>

        <div className="form-group">
          <label>Destination Folder (optional - leave empty for in-place):</label>
          <div className="destination-input">
            <input
              type="text"
              value={destination}
              onChange={(e) => setDestination(e.target.value)}
              placeholder="/path/to/organized (optional)"
              readOnly
              disabled={organizing}
            />
            <button onClick={pickDestination} type="button" disabled={organizing} className="btn-secondary">
              Browse...
            </button>
          </div>
        </div>

        <div className="form-group">
          <label>Mode:</label>
          <div className="radio-group">
            <label>
              <input
                type="radio"
                name="mode"
                value="move"
                checked={mode === 'move'}
                onChange={() => setMode('move')}
                disabled={organizing}
              />
              Move (files are moved into genre folders)
            </label>
            <label>
              <input
                type="radio"
                name="mode"
                value="copy"
                checked={mode === 'copy'}
                onChange={() => setMode('copy')}
                disabled={organizing}
              />
              Copy (files are copied, originals kept)
            </label>
          </div>
        </div>

        <div className="form-group">
          <label>Genre Level:</label>
          <select
            value={level}
            onChange={(e) => setLevel(e.target.value)}
            disabled={organizing}
          >
            <option value="general">General (Electronic, Rock, Classical, etc.)</option>
            <option value="specific">Specific (House, Techno, Punk, etc.)</option>
          </select>
        </div>

        <div className="form-group">
          <label>Profile:</label>
          <select
            value={profile}
            onChange={(e) => setProfile(e.target.value)}
            disabled={organizing}
          >
            <option value="default">Default</option>
            <option value="cdj-safe">CDJ-safe (max 500 files per folder)</option>
          </select>
        </div>

        <div className="form-group">
          <label>
            <input
              type="checkbox"
              checked={skipExisting}
              onChange={(e) => setSkipExisting(e.target.checked)}
              disabled={organizing}
            />
            Skip existing files (do not overwrite)
          </label>
        </div>

        <div className="form-group">
          <label>
            <input
              type="checkbox"
              checked={dryRun}
              onChange={(e) => setDryRun(e.target.checked)}
              disabled={organizing}
            />
            Dry run (simulate without moving/copying)
          </label>
        </div>

        <button
          onClick={handleOrganize}
          disabled={organizing || !source.trim()}
          className="btn-primary btn-lg btn-block"
        >
          {organizing ? <Spinner size="small" /> : 'Organize'}
        </button>
      </div>

      {result && (
        <div className="result">
          <h2>Organization Complete</h2>
          <div className="result-stats">
            <p><strong>Total files:</strong> {result.summary.total}</p>
            <p><strong>Processed:</strong> {result.summary.processed}</p>
            <p><strong>Moved/Copied:</strong> {result.summary.moved_or_copied}</p>
            <p><strong>Unknown genre:</strong> {result.summary.unknown_count}</p>
          </div>
          {result.warnings && result.warnings.length > 0 && (
            <div className="warnings">
              <h4>Warnings:</h4>
              <ul>
                {result.warnings.map((w, i) => (
                  <li key={i}>{w}</li>
                ))}
              </ul>
            </div>
          )}
          {result.csv_report_path && (
            <p>CSV report saved to: {result.csv_report_path}</p>
          )}
        </div>
      )}
    </div>
  );
}
