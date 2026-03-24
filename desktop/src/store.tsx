import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import type { DownloadTask, AuthStatus } from './types';
import * as api from './api';

interface AppState {
  isAuthenticated: boolean;
  setIsAuthenticated: (value: boolean) => void;
  checkAuth: () => Promise<void>;
  activeTasks: DownloadTask[];
  refreshTasks: () => Promise<void>;
  addTask: (task: DownloadTask) => void;
  updateTask: (taskId: string, updates: Partial<DownloadTask>) => void;
}

const AppContext = createContext<AppState | undefined>(undefined);

export function AppProvider({ children }: { children: ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [activeTasks, setActiveTasks] = useState<DownloadTask[]>([]);

  const checkAuth = async () => {
    try {
      const status: AuthStatus = await api.getAuthStatus();
      setIsAuthenticated(status.connected);
    } catch (err) {
      console.error('Auth check failed:', err);
      setIsAuthenticated(false);
    }
  };

  const refreshTasks = async () => {
    try {
      const tasks = await api.listDownloads(100);
      setActiveTasks(tasks);
    } catch (err) {
      console.error('Failed to fetch tasks:', err);
    }
  };

  const addTask = (task: DownloadTask) => {
    setActiveTasks((prev) => [task, ...prev]);
  };

  const updateTask = (taskId: string, updates: Partial<DownloadTask>) => {
    setActiveTasks((prev) =>
      prev.map((t) => (t.task_id === taskId ? { ...t, ...updates } : t))
    );
  };

  // Check auth on mount
  useEffect(() => {
    checkAuth();
  }, []);

  // Poll active tasks every 3 seconds if any are downloading
  useEffect(() => {
    const hasDownloading = activeTasks.some(
      (t) => t.status === 'downloading' || t.status === 'queued'
    );
    if (!hasDownloading) return;

    const interval = setInterval(refreshTasks, 3000);
    return () => clearInterval(interval);
  }, [activeTasks]);

  return (
    <AppContext.Provider
      value={{
        isAuthenticated,
        setIsAuthenticated,
        checkAuth,
        activeTasks,
        refreshTasks,
        addTask,
        updateTask,
      }}
    >
      {children}
    </AppContext.Provider>
  );
}

export function useApp() {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error('useApp must be used within AppProvider');
  return ctx;
}
