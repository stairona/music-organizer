import { Routes, Route } from 'react-router-dom';
import { AppProvider } from './store';
import { Navbar } from './components/Navbar';
import { Home } from './screens/Home';
import { Download } from './screens/Download';
import { Downloads } from './screens/Downloads';
import { History } from './screens/History';
import { Organize } from './screens/Organize';

function AppRoutes() {
  return (
    <div className="app">
      <Navbar />
      <main className="main-content">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/download" element={<Download />} />
          <Route path="/downloads" element={<Downloads />} />
          <Route path="/history" element={<History />} />
          <Route path="/organize" element={<Organize />} />
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
