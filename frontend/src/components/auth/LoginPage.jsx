import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import apiClient from '../../services/apiClient';
import { useAppStore } from '../../store/appStore';
import { connectWs } from '../../services/wsClient';

export default function LoginPage() {
  const navigate = useNavigate();
  const profiles = useAppStore((s) => s.profiles);
  const setProfiles = useAppStore((s) => s.setProfiles);
  const selectedProfileName = useAppStore((s) => s.selectedProfileName);
  const setSelectedProfileName = useAppStore((s) => s.setSelectedProfileName);
  const setSession = useAppStore((s) => s.setSession);

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    apiClient
      .get('/profiles')
      .then((resp) => {
        setProfiles(resp.data);
        if (resp.data.length && !selectedProfileName) {
          setSelectedProfileName(resp.data[0].name);
        }
      })
      .catch(() => setError('Could not load server profiles'));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const submit = async (e) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const resp = await apiClient.post('/auth/login', {
        profile_name: selectedProfileName,
        username,
        password,
      });
      const session = {
        token: resp.data.session_token,
        username: resp.data.username,
        profileName: selectedProfileName,
      };
      setSession(session);
      connectWs(session.token);
      navigate('/summary');
    } catch (err) {
      setError(err.response?.data?.detail || 'Authentication failed');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="login-wrap">
      <div className="card">
        <h2>Haulage Event Simulator</h2>
        <form onSubmit={submit}>
          <label>Server profile</label>
          <select
            value={selectedProfileName || ''}
            onChange={(e) => setSelectedProfileName(e.target.value)}
          >
            {profiles.map((p) => (
              <option key={p.name} value={p.name}>
                {p.name} ({p.api_base_url})
              </option>
            ))}
          </select>

          <label>Username</label>
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
          />

          <label>Password</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
          />

          {error && <div className="notice err">{error}</div>}

          <div style={{ marginTop: 12 }}>
            <button type="submit" disabled={submitting || !selectedProfileName}>
              {submitting ? 'Signing in…' : 'Sign in'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
