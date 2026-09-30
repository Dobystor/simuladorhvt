import { useState } from 'react';
import { useAppStore } from '../../store/appStore';

const STATUS_LABELS = {
  0: 'WeighingMachine',
  1: 'Load',
  2: 'Unload',
  3: 'InTransit',
  4: 'Stop',
};

function FeedRow({ row }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <>
      <tr onClick={() => setExpanded((e) => !e)} style={{ cursor: 'pointer' }}>
        <td>{row.received_at}</td>
        <td>{row.server_profile}</td>
        <td>{row.mac_vehicle || '—'}</td>
        <td>{STATUS_LABELS[row.status] ?? row.status ?? '—'}</td>
        <td>
          <span className={`badge ${row.is_simulated ? 'sim' : 'ext'}`}>
            {row.is_simulated ? 'Simulated' : 'External'}
          </span>
        </td>
      </tr>
      {expanded && (
        <tr>
          <td colSpan={5}>
            <pre style={{ whiteSpace: 'pre-wrap', margin: 0 }}>
              {row.raw_payload}
            </pre>
          </td>
        </tr>
      )}
    </>
  );
}

export default function EventFeedPage() {
  const eventFeed = useAppStore((s) => s.eventFeed);
  const connectionStatus = useAppStore((s) => s.connectionStatus);
  const session = useAppStore((s) => s.session);

  const profileStatus = session
    ? connectionStatus[session.profileName]?.status
    : null;
  const disconnected = profileStatus && profileStatus !== 'connected';

  return (
    <div>
      <h2>Live Feed</h2>
      {disconnected && (
        <div className="notice warn">Disconnected — reconnecting…</div>
      )}
      <div className="card">
        {eventFeed.length === 0 ? (
          <div className="muted">No events received yet.</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Received</th>
                <th>Profile</th>
                <th>Vehicle</th>
                <th>Status</th>
                <th>Source</th>
              </tr>
            </thead>
            <tbody>
              {eventFeed.map((row, i) => (
                <FeedRow key={row.id ?? i} row={row} />
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
