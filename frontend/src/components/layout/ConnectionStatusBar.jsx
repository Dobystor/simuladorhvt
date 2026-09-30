import { useAppStore } from '../../store/appStore';

export default function ConnectionStatusBar() {
  const connectionStatus = useAppStore((s) => s.connectionStatus);
  const entries = Object.entries(connectionStatus);

  if (entries.length === 0) return null;

  return (
    <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
      {entries.map(([profile, status]) => (
        <span key={profile} className={`badge ${status}`} title={`${profile}: ${status}`}>
          {profile}: {status}
        </span>
      ))}
    </div>
  );
}
