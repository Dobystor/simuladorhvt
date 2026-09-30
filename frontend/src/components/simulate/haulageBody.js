import { resolveVehicleMac, resolveEmployeeMac } from './EntitySelectors';

// Build the common request body for /api/simulate/haulage.
// Returns { body } or { error }.
export function buildHaulageBody({
  eventType,
  vehicle,
  beacon,
  employee,
  mode,
  dateStatusInput,
  extra = {},
}) {
  if (!vehicle) return { error: 'Select a vehicle first.' };
  const macVehicle = resolveVehicleMac(vehicle);
  if (!macVehicle) return { error: 'Vehicle has no addressable tag.' };
  if (!mode) return { error: 'Select a simulation mode.' };

  let dateStatus = null;
  if (mode === 'Offline') {
    if (!dateStatusInput) return { error: 'Offline mode requires a DateStatus.' };
    const dt = new Date(dateStatusInput);
    if (!(dt < new Date())) return { error: 'DateStatus must be in the past.' };
    dateStatus = dt.toISOString();
  }

  return {
    body: {
      event_type: eventType,
      mac_vehicle: macVehicle,
      mac_beacon: beacon ? beacon.mac.toUpperCase() : null,
      mac_operator: employee ? resolveEmployeeMac(employee) : null,
      mode,
      date_status: dateStatus,
      ...extra,
    },
  };
}

export function modeReady(mode, dateStatusInput) {
  if (mode === 'Online') return true;
  if (mode === 'Offline') {
    return Boolean(dateStatusInput) && new Date(dateStatusInput) < new Date();
  }
  return false;
}
