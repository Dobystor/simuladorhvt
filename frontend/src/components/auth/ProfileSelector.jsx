import { useEffect } from 'react';
import apiClient from '../../services/apiClient';
import { useAppStore } from '../../store/appStore';

export default function ProfileSelector() {
  const profiles = useAppStore((s) => s.profiles);
  const selected = useAppStore((s) => s.selectedProfileName);
  const setProfiles = useAppStore((s) => s.setProfiles);
  const setSelected = useAppStore((s) => s.setSelectedProfileName);

  useEffect(() => {
    apiClient
      .get('/profiles')
      .then((res) => {
        setProfiles(res.data);
        if (res.data.length > 0 && !selected) {
          setSelected(res.data[0].name);
        }
      })
      .catch(() => setProfiles([]));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="field">
      <label htmlFor="profile">SmartFlow Server</label>
      <select
        id="profile"
        value={selected || ''}
        onChange={(e) => setSelected(e.target.value)}
      >
        {profiles.length === 0 && <option value="">No profiles configured</option>}
        {profiles.map((p) => (
          <option key={p.name} value={p.name}>
            {p.name} ({p.api_base_url})
          </option>
        ))}
      </select>
    </div>
  );
}
