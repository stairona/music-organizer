import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useApp } from '../store';
import { getAuthLoginUrl, exchangeAuthCode } from '../api';
import { Spinner, ErrorAlert } from '../components';
import './Login.css';

export function Login() {
  const { setIsAuthenticated } = useApp();
  const navigate = useNavigate();

  const [code, setCode] = useState('');
  const [authUrl, setAuthUrl] = useState<string | null>(null);
  const [codeVerifier, setCodeVerifier] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const initiateLogin = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getAuthLoginUrl();
      setAuthUrl(res.auth_url);
      setCodeVerifier(res.code_verifier);
    } catch (err: any) {
      setError(err.message || 'Failed to get auth URL');
    } finally {
      setLoading(false);
    }
  };

  const submitCode = async () => {
    if (!code.trim() || !codeVerifier) {
      setError('Please enter the code from Spotify');
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const res = await exchangeAuthCode(code.trim(), codeVerifier);
      if (res.success) {
        setIsAuthenticated(true);
        navigate('/playlists');
      } else {
        setError('Authentication failed');
      }
    } catch (err: any) {
      setError(err.message || 'Failed to exchange code');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login">
      <div className="login-card">
        <h1>Connect Spotify</h1>

        {!authUrl ? (
          <div className="login-step">
            <p>
              Click the button below to open Spotify and authorize this app.
              After authorizing, you'll receive a code to paste below.
            </p>
            <button
              onClick={initiateLogin}
              disabled={loading}
              className="btn-primary large"
            >
              {loading ? <Spinner size="small" /> : 'Open Spotify Login'}
            </button>
          </div>
        ) : (
          <div className="login-step">
            <p>
              1. Open the link in your browser (or the browser should have opened automatically):
            </p>
            <a href={authUrl} target="_blank" rel="noopener noreferrer" className="auth-link">
              Open Spotify Authorization
            </a>
            <p className="note">
              2. After logging in and approving, Spotify will display a <strong>code</strong>.
              3. Copy that code and paste it below.
            </p>
            <textarea
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="Paste code here..."
              rows={3}
              className="code-input"
            />
            <button
              onClick={submitCode}
              disabled={loading || !code.trim()}
              className="btn-primary large"
            >
              {loading ? <Spinner size="small" /> : 'Confirm & Connect'}
            </button>
          </div>
        )}

        {error && (
          <ErrorAlert message={error} onDismiss={() => setError(null)} />
        )}
      </div>
    </div>
  );
}
