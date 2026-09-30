import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import apiClient from '../../services/apiClient';

const STATUS_LABELS = {
  0: 'WeighingMachine',
  1: 'Load',
  2: 'Unload',
  3: 'InTransit',
  4: 'Stop',
};

export default function PostLoginSummary() {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    apiClient
      .get('/summary')
      .then((resp) => setData(resp.data))
      .catch((err) =>
        setError(err.response?.data?.detail || 'Could not load summary')
      );
  }, []);

  if (error) return <div className="notice err">{error}</div>;
  if (!data) return <div className="muted">Loading summary…</div>;

  return (
    <div>
      <h2>Events since last login</h2>
      <p className="muted">Since: {data.since}</p>
      {data.groups.length === 0 ? (
        <div className="notice ok">No new haulage events since your last login.</div>
      ) : (
        data.groups.map((g) => (
          <div className="card" key={g.mac_vehicle}>
            <div className="row" style={{ justifyContent: 'space-between' }}>
              <strong>{g.mac_vehicle}</strong>
              <button
                className="secondary"
                onClick={() =>
                  navigate('/simulate', { state: { macVehicle: g.mac_vehicle } })
                }
              >
                Simulate
              </button>
            </div>
            <table>
              <thead>
                <tr>
                  <th>Received</th>
                  <th>Status</th>
                  <th>Beacon</th>
                  <th>Source</th>
                </tr>
              </thead>
              <tbody>
                {g.events.map((e, i) => (
                  <tr key={i}>
                    <td>{e.received_at}</td>
                    <td>{STATUS_LABELS[e.status] ?? e.status}</td>
                    <td>{e.mac_beacon || '—'}</td>
                    <td>
                      <span className={`badge ${e.is_simulated ? 'sim' : 'ext'}`}>
                        {e.is_simulated ? 'Simulated' : 'External'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ))
      )}
    </div>
  );
}
