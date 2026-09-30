import { useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate, Outlet } from 'react-router-dom';
import { useAppStore } from './store/appStore';
import { connectWebSocket, disconnectWebSocket } from './services/wsClient';
import AppShell from './components/layout/AppShell';
import LoginPage from './pages/LoginPage';
import PostLoginSummary from './pages/PostLoginSummary';
import SimulatePage from './pages/SimulatePage';
import EventLogPage from './pages/EventLogPage';
import EventFeedPage from './pages/EventFeedPage';

function RequireAuth() {
  const session = useAppStore((s) => s.session);
  if (!session) return <Navigate to="/login" replace />;
  return <Outlet />;
}

export default function App() {
  const session = useAppStore((s) => s.session);

  // Reconnect the WebSocket on load if a session was restored from storage.
  useEffect(() => {
    if (session?.token) {
      connectWebSocket(session.token);
    }
    return () => disconnectWebSocket();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route element={<RequireAuth />}>
          <Route element={<AppShell />}>
            <Route path="/summary" element={<PostLoginSummary />} />
            <Route path="/simulate" element={<SimulatePage />} />
            <Route path="/history/log" element={<EventLogPage />} />
            <Route path="/history/feed" element={<EventFeedPage />} />
          </Route>
        </Route>
        <Route path="*" element={<Navigate to={session ? '/summary' : '/login'} replace />} />
      </Routes>
    </BrowserRouter>
  );
}
