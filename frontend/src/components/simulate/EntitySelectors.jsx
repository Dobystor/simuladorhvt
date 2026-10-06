import { useAppStore } from '../../store/appStore';

// beaconFilter: optional (beacon) => bool to restrict the beacon dropdown.
export default function EntitySelectors({
  entities,
  errors,
  reload,
  showBeacon = true,
  showEmployee = true,
  beaconFilter = null,
}) {
  const selectedVehicle = useAppStore((s) => s.selectedVehicle);
  const selectedBeacon = useAppStore((s) => s.selectedBeacon);
  const selectedEmployee = useAppStore((s) => s.selectedEmployee);
  const setField = useAppStore((s) => s.setSimulationFormField);

  const manualMode = useAppStore((s) => s.manualMacEntry);
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
              <li key={type}>
                <strong>{type}</strong>: {msg}
              </li>
            ))}
          </ul>
          <button onClick={reload}>Retry loading entities</button>
        </div>
      )}

      {/* Manual MAC toggle */}
      <div className="field" style={{ marginBottom: 14 }}>
        <label style={{ display: 'flex', gap: 8, alignItems: 'center', textTransform: 'none' }}>
          <input
            type="checkbox"
            checked={manualMode}
            onChange={(e) => setField('manualMacEntry', e.target.checked)}
            style={{ width: 'auto' }}
          />
          Enter MACs manually
        </label>
      </div>

      {manualMode ? (
        <div className="row">
          <div className="col">
            <label>Vehicle MAC</label>
            <input
              placeholder="AA:BB:CC:DD:EE:FF"
              value={manualMacVehicle}
              onChange={(e) => setField('manualMacVehicle', e.target.value)}
            />
          </div>
          {showBeacon && (
            <div className="col">
              <label>Beacon MAC</label>
              <input
                placeholder="AA:BB:CC:DD:EE:FF"
                value={manualMacBeacon}
                onChange={(e) => setField('manualMacBeacon', e.target.value)}
              />
            </div>
          )}
          {showEmployee && (
            <div className="col">
              <label>Operator MAC (optional)</label>
              <input
                placeholder="AA:BB:CC:DD:EE:FF"
                value={manualMacOperator}
                onChange={(e) => setField('manualMacOperator', e.target.value)}
              />
            </div>
          )}
        </div>
      ) : (
        <div className="row">
          <div className="col">
            <label>Vehicle</label>
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
          </div>

          {showBeacon && (
            <div className="col">
              <label>Beacon</label>
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
            </div>
          )}

          {showEmployee && (
            <div className="col">
              <label>Operator (optional)</label>
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
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ---- MAC resolution helpers (consider manual entry first) ----

function manual(field) {
  return useAppStore.getState()[field]?.trim().toUpperCase() || null;
}

export function resolveTagMac(tag) {
  if (!tag) return null;
  if (tag.swarm_id) return tag.swarm_id.toUpperCase();
  if (tag.bluetooth_address) return tag.bluetooth_address.toUpperCase();
  return null;
}

export function vehicleMac(vehicle) {
  const state = useAppStore.getState();
  if (state.manualMacEntry) return manual('manualMacVehicle');
  if (!vehicle) return null;
  if (vehicle.mac) return vehicle.mac.toUpperCase();
  if (vehicle.mac_vehicle) return vehicle.mac_vehicle.toUpperCase();
  return resolveTagMac(vehicle.smart_flow_tag);
}

export function beaconMac(beacon) {
  const state = useAppStore.getState();
  if (state.manualMacEntry) return manual('manualMacBeacon');
  if (!beacon) return null;
  return beacon.mac ? beacon.mac.toUpperCase() : null;
}

export function employeeMac(employee) {
  const state = useAppStore.getState();
  if (state.manualMacEntry) return manual('manualMacOperator');
  if (!employee) return null;
  if (employee.mac) return employee.mac.toUpperCase();
  const tags = employee.smart_flow_tags || [];
  for (const t of tags) {
    const mac = resolveTagMac(t);
    if (mac) return mac;
  }
  return null;
}
