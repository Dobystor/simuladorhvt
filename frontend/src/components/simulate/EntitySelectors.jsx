import { useAppStore } from '../../store/appStore';

/**
 * Each entity field (Vehicle, Beacon, Operator) has its own toggle between
 * dropdown selection and manual MAC entry, so you can mix and match.
 */
export default function EntitySelectors({
  entities,
  errors,
  reload,
  showBeacon = true,
  showEmployee = true,
  beaconFilter = null,
}) {
  const setField = useAppStore((s) => s.setSimulationFormField);

  const selectedVehicle = useAppStore((s) => s.selectedVehicle);
  const selectedBeacon = useAppStore((s) => s.selectedBeacon);
  const selectedEmployee = useAppStore((s) => s.selectedEmployee);
  const manualVehicle = useAppStore((s) => s.manualVehicle);
  const manualBeacon = useAppStore((s) => s.manualBeacon);
  const manualOperator = useAppStore((s) => s.manualOperator);
  const manualMacVehicle = useAppStore((s) => s.manualMacVehicle);
  const manualMacBeacon = useAppStore((s) => s.manualMacBeacon);
  const manualMacOperator = useAppStore((s) => s.manualMacOperator);

  const beacons = beaconFilter ? entities.beacons.filter(beaconFilter) : entities.beacons;
  const errorEntries = Object.entries(errors || {});

  return (
    <div>
      {errorEntries.length > 0 && (
        <div className="banner err">
          <div>Some entities failed to load:</div>
          <ul style={{ margin: '6px 0' }}>
            {errorEntries.map(([type, msg]) => (
              <li key={type}><strong>{type}</strong>: {msg}</li>
            ))}
          </ul>
          <button onClick={reload}>Retry loading entities</button>
        </div>
      )}

      <div className="row">
        {/* ---- Vehicle ---- */}
        <div className="col">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <label>Vehicle</label>
            <FieldToggle checked={manualVehicle} onChange={(v) => setField('manualVehicle', v)} />
          </div>
          {manualVehicle ? (
            <input
              placeholder="Vehicle MAC (AA:BB:CC:DD:EE:FF)"
              value={manualMacVehicle}
              onChange={(e) => setField('manualMacVehicle', e.target.value)}
            />
          ) : (
            <>
              <select
                value={selectedVehicle?.id ?? ''}
                onChange={(e) => {
                  const v = entities.vehicles.find((x) => String(x.id) === e.target.value);
                  setField('selectedVehicle', v || null);
                }}
              >
                <option value="">— Select vehicle —</option>
                {entities.vehicles.map((v) => (
                  <option key={v.id} value={v.id}>
                    {v.name} (type {v.type}){v.has_tag ? '' : ' — ⚠ NO TAG'}
                  </option>
                ))}
              </select>
              {selectedVehicle && selectedVehicle.has_tag === false && (
                <div className="error">This vehicle has no assigned tag (no MAC).</div>
              )}
            </>
          )}
        </div>

        {/* ---- Beacon ---- */}
        {showBeacon && (
          <div className="col">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <label>Beacon</label>
              <FieldToggle checked={manualBeacon} onChange={(v) => setField('manualBeacon', v)} />
            </div>
            {manualBeacon ? (
              <input
                placeholder="Beacon MAC (AA:BB:CC:DD:EE:FF)"
                value={manualMacBeacon}
                onChange={(e) => setField('manualMacBeacon', e.target.value)}
              />
            ) : (
              <select
                value={selectedBeacon?.id ?? ''}
                onChange={(e) => {
                  const b = beacons.find((x) => String(x.id) === e.target.value);
                  setField('selectedBeacon', b || null);
                }}
              >
                <option value="">— Select beacon —</option>
                {beacons.map((b) => (
                  <option key={b.id} value={b.id}>
                    {b.name} ({b.mac})
                  </option>
                ))}
              </select>
            )}
          </div>
        )}

        {/* ---- Operator ---- */}
        {showEmployee && (
          <div className="col">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <label>Operator (optional)</label>
              <FieldToggle checked={manualOperator} onChange={(v) => setField('manualOperator', v)} />
            </div>
            {manualOperator ? (
              <input
                placeholder="Operator MAC (AA:BB:CC:DD:EE:FF)"
                value={manualMacOperator}
                onChange={(e) => setField('manualMacOperator', e.target.value)}
              />
            ) : (
              <select
                value={selectedEmployee?.id ?? ''}
                onChange={(e) => {
                  const emp = entities.employees.find((x) => String(x.id) === e.target.value);
                  setField('selectedEmployee', emp || null);
                }}
              >
                <option value="">— None —</option>
                {entities.employees.map((emp) => (
                  <option key={emp.id} value={emp.id}>
                    {emp.name}{emp.has_tag ? '' : ' — ⚠ no tag'}
                  </option>
                ))}
              </select>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

/** Small toggle label for "Manual" per field. */
function FieldToggle({ checked, onChange }) {
  return (
    <label style={{
      display: 'flex', gap: 5, alignItems: 'center',
      fontSize: 11, color: 'var(--text-dim)', cursor: 'pointer',
      textTransform: 'none', letterSpacing: 0, fontWeight: 400,
    }}>
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        style={{ width: 'auto' }}
      />
      Manual
    </label>
  );
}

// ---- MAC resolution helper (exported for useResolvedMacs) ----
export function resolveTagMac(tag) {
  if (!tag) return null;
  if (tag.swarm_id) return tag.swarm_id.toUpperCase();
  if (tag.bluetooth_address) return tag.bluetooth_address.toUpperCase();
  return null;
}
