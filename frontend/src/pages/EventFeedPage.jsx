import { useState } from 'react';
import { useAppStore } from '../store/appStore';

const STATUS_LABELS = {
  0: 'WeighingMachine',
  1: 'Load',
  2: 'Unload',
  3: 'InTransit',
  4: 'Stop',
};

function FeedRow({ evt }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <tr onClick={() => setOpen((o) => !o)} style={{ cursor: 'pointer' }}>
        <td>{evt.received_at ? new Date(evt.received_at).toLocaleString() : '—'}</td>
        <td>{evt.server_profile}</td>
        <td>{evt.mac_vehicle || '—'}</td>
        <td>{STATUS_LABELS[evt.status] ?? evt.status ?? '—'}</td>
        <td>
          <span className={`badge ${evt.is_simulated ? 'sim' : 'ext'}`}>
            {evt.is_simulated ? 'Simulated' : 'Hardware'}
          </span>
        </td>
      </tr>
      {open && (
        <tr>
          <td colSpan={5}>
            <pre style={{ margin: 0, whiteSpace: 'pre-wrap', fontSize: 12 }}>
              {evt.raw_payload || JSON.stringify(evt, null, 2)}
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

  const status = session ? connectionStatus[session.profileName] : null;
  const disconnected = status && status !== 'connected';

  return (
    <div>
      <h2>Live Feed</h2>
      {disconnected && (
        <div className="banner warn">Disconnected — reconnecting… ({status})</div>
      )}
      <div className="panel">
        {eventFeed.length === 0 ? (
          <div className="muted">No events received yet. New bus events appear here in real time.</div>
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
              {eventFeed.map((evt, i) => (
                <FeedRow key={evt.id ?? i} evt={evt} />
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
