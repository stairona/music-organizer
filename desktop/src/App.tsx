import { Routes, Route, Navigate } from 'react-router-dom';
import { AppProvider, useApp } from './store';
import { Navbar } from './components/Navbar';
import { Home } from './screens/Home';
import { Login } from './screens/Login';
import { Playlists } from './screens/Playlists';
import { Downloads } from './screens/Downloads';
import { History } from './screens/History';

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useApp();
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}

function AppRoutes() {
  const { isAuthenticated } = useApp();

  return (
    <div className="app">
      {isAuthenticated && <Navbar />}
      <main className="main-content">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/login" element={<Login />} />
          <Route
            path="/playlists"
            element={
              <ProtectedRoute>
                <Playlists />
              </ProtectedRoute>
            }
          />
          <Route
            path="/downloads"
            element={
              <ProtectedRoute>
                <Downloads />
              </ProtectedRoute>
            }
          />
          <Route
            path="/history"
            element={
              <ProtectedRoute>
                <History />
              </ProtectedRoute>
            }
          />
        </Routes>
      </main>
    </div>
  );
}

function App() {
  return (
    <AppProvider>
      <AppRoutes />
    </AppProvider>
  );
}

export default App;
