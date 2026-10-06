import { useEffect, useState } from 'react';
import apiClient from '../../services/apiClient';
import { useAppStore } from '../../store/appStore';

export default function ProfileSelector() {
  const profiles = useAppStore((s) => s.profiles);
  const selected = useAppStore((s) => s.selectedProfileName);
  const setProfiles = useAppStore((s) => s.setProfiles);
  const setSelected = useAppStore((s) => s.setSelectedProfileName);

  const [showAdd, setShowAdd] = useState(false);
  const [newName, setNewName] = useState('');
  const [newHost, setNewHost] = useState('');
  const [adding, setAdding] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadServers();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function loadServers() {
    apiClient
      .get('/servers')
      .then((res) => {
        setProfiles(res.data);
        if (res.data.length > 0 && !selected) {
          setSelected(res.data[0].name);
        }
      })
      .catch(() => setProfiles([]));
  }

  async function handleAdd() {
    setError(null);
    const host = newHost.trim();
    const name = newName.trim() || host;
    if (!host) {
      setError('Enter the server IP or hostname.');
      return;
    }
    setAdding(true);
    try {
      await apiClient.post('/servers', {
        name,
        api_url: host.startsWith('http') ? host : `https://${host}`,
        rabbitmq_host: host.replace(/^https?:\/\//, '').split('/')[0].split(':')[0],
        rethinkdb_host: host.replace(/^https?:\/\//, '').split('/')[0].split(':')[0],
      });
      setShowAdd(false);
      setNewName('');
      setNewHost('');
      loadServers();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to add server');
    } finally {
      setAdding(false);
    }
  }

  async function handleDelete(id, serverName) {
    if (!window.confirm(`Remove server "${serverName}"?`)) return;
    try {
      await apiClient.delete(`/servers/${id}`);
      loadServers();
    } catch {
      // ignore
    }
  }

  if (showAdd) {
    return (
      <div>
        <label style={{ marginBottom: 12 }}>Register new server</label>
        <div className="field">
          <label>Server name (optional)</label>
          <input
            placeholder="e.g. Production"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
          />
        </div>
        <div className="field">
          <label>IP / Hostname</label>
          <input
            placeholder="e.g. 10.174.109.16"
            value={newHost}
            onChange={(e) => setNewHost(e.target.value)}
          />
        </div>
        {error && <div className="error">{error}</div>}
        <div style={{ display: 'flex', gap: 10, marginTop: 10 }}>
          <button onClick={() => setShowAdd(false)}>Cancel</button>
          <button className="primary" disabled={adding} onClick={handleAdd}>
            {adding ? 'Adding…' : 'Add & continue'}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="field">
        <label htmlFor="profile">SmartFlow Server</label>
        <select
          id="profile"
          value={selected || ''}
          onChange={(e) => setSelected(e.target.value)}
        >
          {profiles.length === 0 && <option value="">No servers configured</option>}
          {profiles.map((p) => (
            <option key={p.name} value={p.name}>
              {p.name} ({p.api_url})
            </option>
          ))}
        </select>
      </div>
      {/* Delete button for dynamic servers */}
      {profiles.some((p) => p.source === 'dynamic' && p.name === selected) && (
        <button
          style={{ marginBottom: 10, color: 'var(--neon-pink)', borderColor: 'rgba(224,90,122,0.3)', fontSize: 12 }}
          onClick={() => {
            const s = profiles.find((p) => p.name === selected);
            if (s?.id) handleDelete(s.id, s.name);
          }}
        >
          Remove this server
        </button>
      )}
      <button
        style={{ width: '100%', marginBottom: 14, borderStyle: 'dashed', borderColor: 'rgba(78,186,138,0.35)', color: 'var(--neon-green)' }}
        onClick={() => setShowAdd(true)}
      >
        + Add server
      </button>
    </div>
  );
}
