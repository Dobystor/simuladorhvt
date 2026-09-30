import { useNavigate } from 'react-router-dom';
import apiClient from '../../services/apiClient';
import { useAppStore } from '../../store/appStore';
import { disconnectWebSocket } from '../../services/wsClient';

export default function SessionHeader() {
  const navigate = useNavigate();
  const session = useAppStore((s) => s.session);
  const clearSession = useAppStore((s) => s.clearSession);

  async function handleLogout() {
    try {
      await apiClient.post('/auth/logout');
    } catch {
      // Ignore; we clear locally regardless.
    }
    disconnectWebSocket();
    clearSession();
    navigate('/login');
  }

  if (!session) return null;

  return (
    <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
      <span className="muted">
        {session.username} @ {session.profileName}
      </span>
      <button onClick={handleLogout}>Logout</button>
    </div>
  );
}
