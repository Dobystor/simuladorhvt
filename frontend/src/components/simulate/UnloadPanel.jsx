import { useEffect, useState } from 'react';
import apiClient from '../../services/apiClient';
import { useAppStore } from '../../store/appStore';
import { useModeValidation } from './ModeSelector';
import EntitySelectors, { vehicleMac, employeeMac } from './EntitySelectors';
import { usePublish } from './usePublish';
import ResultBanner from './ResultBanner';

// Beacons mapped to Unload-type HaulageSites (best-effort filter by ref id).
function unloadBeaconFilter(entities) {
  const unloadRefIds = new Set(
    (entities.haulageSites || [])
      .filter((s) => (s.type || '').toLowerCase().includes('unload'))
      .map((s) => s.reference_point_id)
  );
  return (b) => unloadRefIds.size === 0 || unloadRefIds.has(b.reference_point_id);
}

function formatElapsed(mins) {
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  return `${h}h ${m}m`;
}

export default function UnloadPanel({ entities, errors, reload }) {
  const vehicle = useAppStore((s) => s.selectedVehicle);
  const beacon = useAppStore((s) => s.selectedBeacon);
  const employee = useAppStore((s) => s.selectedEmployee);
  const mode = useModeValidation();
  const { result, busy, publish } = usePublish();

  const macVehicle = vehicleMac(vehicle);
  const [loadInfo, setLoadInfo] = useState(null);

  useEffect(() => {
    if (!macVehicle) {
      setLoadInfo(null);
      return;
    }
    apiClient
      .get('/history/logs', { params: { mac_vehicle: macVehicle, event_type: 'Load' } })
      .then((res) => {
        const records = res.data.records || [];
        if (records.length === 0) {
          setLoadInfo({ found: false });
          return;
        }
        const latest = records[0]; // reverse-chronological
        const loadTs = new Date(latest.published_at).getTime();
        const mins = Math.floor((Date.now() - loadTs) / 60000);
        setLoadInfo({ found: true, minutes: mins, over18h: mins > 18 * 60 });
      })
      .catch(() => setLoadInfo(null));
  }, [macVehicle]);

  const canPublish = macVehicle && beacon && mode.valid && !busy;

  async function handlePublish() {
    await publish('/simulate/haulage', {
      event_type: 'Unload',
      mac_vehicle: macVehicle,
      mac_beacon: beacon.mac.toUpperCase(),
      mac_operator: employeeMac(employee),
      mode: mode.mode,
      date_status: mode.dateStatusIso,
    });
  }

  return (
    <div>
      <EntitySelectors
        entities={entities}
        errors={errors}
        reload={reload}
        beaconFilter={unloadBeaconFilter(entities)}
      />

      {loadInfo?.found && (
        <div style={{ marginTop: 10 }}>
          <span className="chip">Since last Load: {formatElapsed(loadInfo.minutes)}</span>
        </div>
      )}
      {loadInfo?.found && loadInfo.over18h && (
        <div className="banner warn">
          Elapsed time exceeds 18 hours — Haulages.API will not create a Haulage record.
        </div>
      )}
      {loadInfo && !loadInfo.found && (
        <div className="banner warn">
          No prior Load event found for this vehicle — Haulages.API may not create a Haulage record.
        </div>
      )}

      <button className="primary" style={{ marginTop: 14 }} disabled={!canPublish} onClick={handlePublish}>
        Publish Unload event
      </button>
      <ResultBanner result={result} />
    </div>
  );
}
