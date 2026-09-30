import { useEffect, useRef, useState } from 'react';
import apiClient from '../../services/apiClient';

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
  const [data, setData] = useState(null);
  const debounceRef = useRef(null);

  const fetchLogs = () => {
    const params = { page };
    Object.entries(filters).forEach(([k, v]) => {
      if (v) params[k] = v;
    });
    apiClient
      .get('/history/logs', { params })
      .then((resp) => setData(resp.data))
      .catch(() => setData({ total: 0, records: [] }));
  };

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(fetchLogs, 300);
    return () => clearTimeout(debounceRef.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters, page]);

  const set = (k, v) => {
    setPage(1);
    setFilters((f) => ({ ...f, [k]: v }));
  };

  const totalPages = data ? Math.max(1, Math.ceil(data.total / 100)) : 1;

  return (
    <div>
      <h2>Event Log</h2>
      <div className="card row">
        <div>
          <label>Username</label>
          <input value={filters.username} onChange={(e) => set('username', e.target.value)} />
        </div>
        <div>
          <label>MAC Vehicle</label>
          <input value={filters.mac_vehicle} onChange={(e) => set('mac_vehicle', e.target.value)} />
        </div>
        <div>
          <label>From (UTC)</label>
          <input type="datetime-local" value={filters.from_dt} onChange={(e) => set('from_dt', e.target.value)} />
        </div>
        <div>
          <label>To (UTC)</label>
          <input type="datetime-local" value={filters.to_dt} onChange={(e) => set('to_dt', e.target.value)} />
        </div>
        <div>
          <label>Event type</label>
          <select value={filters.event_type} onChange={(e) => set('event_type', e.target.value)}>
            {EVENT_TYPES.map((t) => (
              <option key={t} value={t}>
                {t || 'All'}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="card">
        {data && data.records.length === 0 ? (
          <div className="notice">No records match the active filters.</div>
        ) : (
          <>
            <p className="muted">Total: {data?.total ?? 0} records</p>
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
                {data?.records.map((r) => (
                  <tr key={r.id}>
                    <td>{r.published_at}</td>
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
            <div className="row" style={{ marginTop: 12, alignItems: 'center' }}>
              <button className="secondary" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
                Previous
              </button>
              <span className="muted">
                Page {page} of {totalPages}
              </span>
              <button
                className="secondary"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
              >
                Next
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
