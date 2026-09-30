import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import apiClient from '../services/apiClient';
import { useAppStore } from '../store/appStore';

const STATUS_LABELS = {
  0: 'WeighingMachine',
  1: 'Load',
  2: 'Unload',
  3: 'InTransit',
  4: 'Stop',
};

export default function PostLoginSummary() {
  const navigate = useNavigate();
  const setSimField = useAppStore((s) => s.setSimulationFormField);
  const [summary, setSummary] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    apiClient
      .get('/summary')
      .then((res) => setSummary(res.data))
      .catch((err) => setError(err.response?.data?.detail || 'Failed to load summary'));
  }, []);

  function simulateFor(macVehicle) {
    setSimField('selectedVehicle', { mac_vehicle: macVehicle });
    navigate('/simulate');
  }

  if (error) return <div className="banner err">{error}</div>;
  if (!summary) return <p className="muted">Loading summary…</p>;

  return (
    <div>
      <h2>Since last login</h2>
      <p className="muted">Events received after {new Date(summary.since).toLocaleString()}</p>

      {summary.groups.length === 0 && (
        <div className="banner ok">No new haulage events since your last login.</div>
      )}

      {summary.groups.map((group) => (
        <div className="card" key={group.mac_vehicle}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h3 style={{ margin: 0 }}>{group.mac_vehicle}</h3>
            <button onClick={() => simulateFor(group.mac_vehicle)}>Simulate follow-up</button>
          </div>
          <table style={{ marginTop: 10 }}>
            <thead>
              <tr>
                <th>Received</th>
                <th>Status</th>
                <th>Beacon</th>
                <th>Source</th>
              </tr>
            </thead>
            <tbody>
              {group.events.map((e, i) => (
                <tr key={i}>
                  <td>{new Date(e.received_at).toLocaleString()}</td>
                  <td>{STATUS_LABELS[e.status] ?? e.status}</td>
                  <td>{e.mac_beacon || '—'}</td>
                  <td>
                    <span className={`badge ${e.is_simulated ? 'sim' : 'ext'}`}>
                      {e.is_simulated ? 'Simulated' : 'Hardware'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
    </div>
  );
}
