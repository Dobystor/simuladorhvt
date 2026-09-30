import { useEffect, useRef, useState } from 'react';
import apiClient from '../services/apiClient';

const EVENT_TYPES = [
  '',
  'Load',
  'Unload',
  'WeighingMachine',
  'InTransit',
  'Stop',
  'LocationBasedUnload',
  'OperatorAssignment',
];

export default function EventLogPage() {
  const [filters, setFilters] = useState({
    username: '',
    mac_vehicle: '',
    from_dt: '',
    to_dt: '',
    event_type: '',
  });
  const [page, setPage] = useState(1);
  const [data, setData] = useState({ total: 0, records: [], page: 1, page_size: 100 });
  const debounceRef = useRef(null);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      const params = { page };
      Object.entries(filters).forEach(([k, v]) => {
        if (v) {
          params[k] = k.endsWith('_dt') ? new Date(v).toISOString() : v;
        }
      });
      apiClient
        .get('/history/logs', { params })
        .then((res) => setData(res.data))
        .catch(() => setData({ total: 0, records: [], page: 1, page_size: 100 }));
    }, 300);
    return () => clearTimeout(debounceRef.current);
  }, [filters, page]);

  function update(field, value) {
    setPage(1);
    setFilters((f) => ({ ...f, [field]: value }));
  }

  const totalPages = Math.max(1, Math.ceil(data.total / data.page_size));

  return (
    <div>
      <h2>Event Log</h2>
      <div className="panel" style={{ marginBottom: 16 }}>
        <div className="row">
          <div className="col">
            <label>Username</label>
            <input value={filters.username} onChange={(e) => update('username', e.target.value)} />
          </div>
          <div className="col">
            <label>MAC Vehicle</label>
            <input value={filters.mac_vehicle} onChange={(e) => update('mac_vehicle', e.target.value)} />
          </div>
          <div className="col">
            <label>Event type</label>
            <select value={filters.event_type} onChange={(e) => update('event_type', e.target.value)}>
              {EVENT_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t || 'All'}
                </option>
              ))}
            </select>
          </div>
        </div>
        <div className="row" style={{ marginTop: 10 }}>
          <div className="col">
            <label>From (UTC)</label>
            <input type="datetime-local" value={filters.from_dt} onChange={(e) => update('from_dt', e.target.value)} />
          </div>
          <div className="col">
            <label>To (UTC)</label>
            <input type="datetime-local" value={filters.to_dt} onChange={(e) => update('to_dt', e.target.value)} />
          </div>
        </div>
      </div>

      <div className="panel">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
          <span className="muted">Total: {data.total} records</span>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <button disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
              Previous
            </button>
            <span className="muted">
              Page {data.page} / {totalPages}
            </span>
            <button disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>
              Next
            </button>
          </div>
        </div>

        {data.records.length === 0 ? (
          <div className="muted">No records match the active filters.</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Published</th>
                <th>User</th>
                <th>Profile</th>
                <th>Type</th>
                <th>Vehicle</th>
                <th>Beacon</th>
                <th>Operator</th>
                <th>Mode</th>
                <th>Weight</th>
              </tr>
            </thead>
            <tbody>
              {data.records.map((r) => (
                <tr key={r.id}>
                  <td>{new Date(r.published_at).toLocaleString()}</td>
                  <td>{r.username}</td>
                  <td>{r.server_profile}</td>
                  <td>{r.event_type}</td>
                  <td>{r.mac_vehicle || '—'}</td>
                  <td>{r.mac_beacon || '—'}</td>
                  <td>{r.mac_operator || '—'}</td>
                  <td>{r.simulation_mode || '—'}</td>
                  <td>{r.gross_weight ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
