import { NavLink } from 'react-router-dom';
import './Navbar.css';

export function Navbar() {
  return (
    <nav className="navbar">
      <div className="navbar-brand">
        <span role="img" aria-label="music">🎵</span> Music Organizer
      </div>
      <div className="navbar-links">
        <NavLink to="/" className={({ isActive }) => isActive ? 'active' : ''}>
          Home
        </NavLink>
        <NavLink to="/download" className={({ isActive }) => isActive ? 'active' : ''}>
          Download
        </NavLink>
        <NavLink to="/downloads" className={({ isActive }) => isActive ? 'active' : ''}>
          Active
        </NavLink>
        <NavLink to="/organize" className={({ isActive }) => isActive ? 'active' : ''}>
          Organize
        </NavLink>
        <NavLink to="/history" className={({ isActive }) => isActive ? 'active' : ''}>
          History
        </NavLink>
      </div>
    </nav>
  );
}
