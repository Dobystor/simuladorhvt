import { useAppStore } from '../../store/appStore';
import SearchableSelect from '../SearchableSelect';

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
              <SearchableSelect
                placeholder="— Select vehicle —"
                value={selectedVehicle?.id ?? ''}
                options={entities.vehicles.map((v) => ({
                  value: v.id,
                  label: `${v.name} (type ${v.type})${v.has_tag ? '' : ' — ⚠ NO TAG'}`,
                }))}
                onChange={(val) => {
                  const v = entities.vehicles.find((x) => String(x.id) === String(val));
                  setField('selectedVehicle', v || null);
                }}
              />
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
              <SearchableSelect
                placeholder="— Select beacon —"
                value={selectedBeacon?.id ?? ''}
                options={beacons.map((b) => ({
                  value: b.id,
                  label: `${b.name} (${b.mac})`,
                }))}
                onChange={(val) => {
                  const b = beacons.find((x) => String(x.id) === String(val));
                  setField('selectedBeacon', b || null);
                }}
              />
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
              <SearchableSelect
                placeholder="— None —"
                value={selectedEmployee?.id ?? ''}
                options={entities.employees.map((emp) => ({
                  value: emp.id,
                  label: `${emp.name}${emp.has_tag ? '' : ' — ⚠ no tag'}`,
                }))}
                onChange={(val) => {
                  const emp = entities.employees.find((x) => String(x.id) === String(val));
                  setField('selectedEmployee', emp || null);
                }}
              />
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
