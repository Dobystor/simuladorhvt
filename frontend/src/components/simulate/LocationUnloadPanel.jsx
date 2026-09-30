import { useState } from 'react';
import { useAppStore } from '../../store/appStore';
import { usePublish } from './usePublish';
import ResultBanner from './ResultBanner';

export default function LocationUnloadPanel({ entities }) {
  const vehicle = useAppStore((s) => s.selectedVehicle);
  const setField = useAppStore((s) => s.setSimulationFormField);
  const { result, busy, publish } = usePublish();
  const [siteId, setSiteId] = useState('');

  const unloadSites = (entities.haulageSites || []).filter((s) =>
    (s.type || '').toLowerCase().includes('unload')
  );
  const type45 = vehicle && (vehicle.type === 4 || vehicle.type === 5);
  const site = unloadSites.find((s) => String(s.id) === siteId);

  const canPublish = type45 && site && vehicle?.id != null && !busy;

  async function handlePublish() {
    await publish('/simulate/location-unload', {
      vehicle_id: vehicle.id,
      haulage_site_id: site.id,
      reference_point_id: site.reference_point_id,
    });
  }

  return (
    <div>
      <div className="row">
        <div className="col">
          <label>Vehicle (type 4 or 5)</label>
          <select
            value={vehicle?.id ?? ''}
            onChange={(e) => {
              const v = entities.vehicles.find((x) => String(x.id) === e.target.value);
              setField('selectedVehicle', v || null);
            }}
          >
            <option value="">— Select vehicle —</option>
            {entities.vehicles.map((v) => (
              <option key={v.id} value={v.id}>
                {v.name} (type {v.type})
              </option>
            ))}
          </select>
        </div>
        <div className="col">
          <label>Unload HaulageSite</label>
          <select value={siteId} onChange={(e) => setSiteId(e.target.value)}>
            <option value="">— Select site —</option>
            {unloadSites.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </div>
      </div>
      {vehicle && !type45 && (
        <div className="error">Location-based unload requires a type 4 or 5 vehicle.</div>
      )}
      <button className="primary" style={{ marginTop: 14 }} disabled={!canPublish} onClick={handlePublish}>
        Send location update
      </button>
      <ResultBanner result={result} />
    </div>
  );
}
