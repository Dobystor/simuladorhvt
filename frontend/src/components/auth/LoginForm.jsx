import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import apiClient from '../../services/apiClient';
import { useAppStore } from '../../store/appStore';
import { connectWebSocket } from '../../services/wsClient';

export default function LoginForm() {
  const navigate = useNavigate();
  const selectedProfileName = useAppStore((s) => s.selectedProfileName);
  const setSession = useAppStore((s) => s.setSession);

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    if (!selectedProfileName) {
      setError('Select a server profile first.');
      return;
    }
    setSubmitting(true);
    try {
      const res = await apiClient.post('/auth/login', {
        profile_name: selectedProfileName,
        username,
        password,
      });
      const session = {
        token: res.data.session_token,
        username: res.data.username,
        profileName: selectedProfileName,
      };
      setSession(session);
      connectWebSocket(session.token);
      navigate('/summary');
    } catch (err) {
      const detail = err.response?.data?.detail;
      setError(detail || 'Authentication failed. Please try again.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <div className="field">
        <label htmlFor="username">Username</label>
        <input
          id="username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          autoComplete="username"
          required
        />
      </div>
      <div className="field">
        <label htmlFor="password">Password</label>
        <input
          id="password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoComplete="current-password"
          required
        />
      </div>
      {error && <div className="error">{error}</div>}
      <button className="primary" type="submit" disabled={submitting} style={{ width: '100%', marginTop: 8 }}>
        {submitting ? 'Signing in…' : 'Sign in'}
      </button>
    </form>
  );
}
