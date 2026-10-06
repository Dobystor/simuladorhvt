import { useState } from 'react';
import { useAppStore } from '../../store/appStore';
import SearchableSelect from '../SearchableSelect';
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
          <SearchableSelect
            placeholder="— Select vehicle —"
            value={vehicle?.id ?? ''}
            options={entities.vehicles.map((v) => ({
              value: v.id,
              label: `${v.name} (type ${v.type})`,
            }))}
            onChange={(val) => {
              const v = entities.vehicles.find((x) => String(x.id) === String(val));
              setField('selectedVehicle', v || null);
            }}
          />
        </div>
        <div className="col">
          <label>Unload HaulageSite</label>
          <SearchableSelect
            placeholder="— Select site —"
            value={siteId}
            options={unloadSites.map((s) => ({ value: s.id, label: s.name }))}
            onChange={(val) => setSiteId(String(val))}
          />
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
