import { useState } from 'react';
import { useAppStore } from '../../store/appStore';
import { useModeValidation } from './ModeSelector';
import EntitySelectors, { vehicleMac } from './EntitySelectors';
import { usePublish } from './usePublish';
import ResultBanner from './ResultBanner';

// Beacons mapped to a WeighingMachine reference point.
function weighingBeaconFilter(entities) {
  const wmRefIds = new Set(
    (entities.weighingMachines || []).map((w) => w.reference_point_id)
  );
  return (b) => wmRefIds.size === 0 || wmRefIds.has(b.reference_point_id);
}

export default function WeighingPanel({ entities, errors, reload }) {
  const vehicle = useAppStore((s) => s.selectedVehicle);
  const beacon = useAppStore((s) => s.selectedBeacon);
  const mode = useModeValidation();
  const { result, busy, publish } = usePublish();

  const [weighingMode, setWeighingMode] = useState('Standard');
  const [weight, setWeight] = useState('');

  const macVehicle = vehicleMac(vehicle);
  const weightNum = parseFloat(weight);
  const weightValid = weightNum > 0 && weightNum <= 999.99;

  // Net/tare classification when EmptyWeight is available.
  let classification = null;
  const emptyWeight = vehicle?.empty_weight;
  if (weighingMode === 'Standard' && weightValid) {
    if (emptyWeight == null) {
      classification = { unavailable: true };
    } else {
      const diff = Math.abs(weightNum - emptyWeight);
      classification = { type: diff > 2.5 ? 'net_load' : 'tare_update' };
    }
  }

  // Find the WeighingMachine matching the selected beacon's reference point.
  const wm = beacon
    ? (entities.weighingMachines || []).find(
        (w) => w.reference_point_id === beacon.reference_point_id
      )
    : null;

  const canPublish =
    macVehicle &&
    beacon &&
    mode.valid &&
    !busy &&
    (weighingMode === 'SimulatedEnabled' || (weightValid && wm));

  async function handlePublish() {
    await publish('/simulate/haulage', {
      event_type: 'WeighingMachine',
      mac_vehicle: macVehicle,
      mac_beacon: beacon.mac.toUpperCase(),
      mode: mode.mode,
      date_status: mode.dateStatusIso,
      weighing_mode: weighingMode,
      gross_weight: weighingMode === 'Standard' ? weightNum : null,
      weighing_machine_rethinkdb_id:
        weighingMode === 'Standard' ? wm?.rethinkdb_id : null,
    });
  }

  return (
    <div>
      <EntitySelectors
        entities={entities}
        errors={errors}
        reload={reload}
        showEmployee={false}
        beaconFilter={weighingBeaconFilter(entities)}
      />

      <div className="field" style={{ marginTop: 12 }}>
        <label>Weighing mode</label>
        <div style={{ display: 'flex', gap: 16 }}>
          <label style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
            <input
              type="radio"
              checked={weighingMode === 'Standard'}
              onChange={() => setWeighingMode('Standard')}
              style={{ width: 'auto' }}
            />
            Standard (write weight)
          </label>
          <label style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
            <input
              type="radio"
              checked={weighingMode === 'SimulatedEnabled'}
              onChange={() => setWeighingMode('SimulatedEnabled')}
              style={{ width: 'auto' }}
            />
            SimulatedEnabled
          </label>
        </div>
      </div>

      {weighingMode === 'Standard' && (
        <div className="field" style={{ maxWidth: 260 }}>
          <label>Gross weight (tonnes, 0 &lt; w ≤ 999.99)</label>
          <input
            type="number"
            step="0.01"
            min="0"
            max="999.99"
            value={weight}
            onChange={(e) => setWeight(e.target.value)}
          />
          {weight && !weightValid && (
            <div className="error">Weight must be greater than 0 and at most 999.99.</div>
          )}
        </div>
      )}

      {classification?.unavailable && (
        <div className="muted">EmptyWeight unavailable — net/tare classification suppressed.</div>
      )}
      {classification?.type && (
        <div className="chip">
          {classification.type === 'net_load' ? 'Net load (> 2.5 t)' : 'Tare update (≤ 2.5 t)'}
        </div>
      )}
      {weighingMode === 'Standard' && beacon && !wm && (
        <div className="error" style={{ marginTop: 8 }}>
          No WeighingMachine maps to the selected beacon's reference point.
        </div>
      )}

      <button className="primary" style={{ marginTop: 14 }} disabled={!canPublish} onClick={handlePublish}>
        Publish WeighingMachine event
      </button>
      <ResultBanner result={result} />
    </div>
  );
}
