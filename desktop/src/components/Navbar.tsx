import { NavLink } from 'react-router-dom';
import { useApp } from '../store';
import './Navbar.css';

export function Navbar() {
  const { isAuthenticated, logout } = useApp();

  const handleLogout = async () => {
    try {
      await fetch('http://localhost:8000/api/v1/auth/logout', {
        method: 'POST',
      });
    } catch (err) {
      console.error('Logout failed:', err);
    } finally {
      window.location.href = '/login';
    }
  };

  return (
    <nav className="navbar">
      <div className="navbar-brand">
        <span role="img" aria-label="music">🎵</span> Music Organizer
      </div>
      <div className="navbar-links">
        <NavLink to="/" className={({ isActive }) => isActive ? 'active' : ''}>
          Home
        </NavLink>
        <NavLink to="/playlists" className={({ isActive }) => isActive ? 'active' : ''}>
          Playlists
        </NavLink>
        <NavLink to="/downloads" className={({ isActive }) => isActive ? 'active' : ''}>
          Downloads
        </NavLink>
        <NavLink to="/history" className={({ isActive }) => isActive ? 'active' : ''}>
          History
        </NavLink>
        {isAuthenticated && (
          <button onClick={handleLogout} className="logout-btn">
            Logout
          </button>
        )}
      </div>
    </nav>
  );
}
