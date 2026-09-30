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
                {v.name} (type {v.type})
              </option>
            ))}
          </select>
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
                  {emp.name}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>
    </div>
  );
}

// Shared helpers to resolve MAC strings from selected entities.
export function resolveTagMac(tag) {
  if (!tag) return null;
  if (tag.swarm_id) return tag.swarm_id.toUpperCase();
  if (tag.bluetooth_address) return tag.bluetooth_address.toUpperCase();
  return null;
}

export function vehicleMac(vehicle) {
  if (!vehicle) return null;
  if (vehicle.mac_vehicle) return vehicle.mac_vehicle.toUpperCase();
  return resolveTagMac(vehicle.smart_flow_tag);
}

export function employeeMac(employee) {
  if (!employee) return null;
  const tags = employee.smart_flow_tags || [];
  for (const t of tags) {
    const mac = resolveTagMac(t);
    if (mac) return mac;
  }
  return null;
}
