import { useAppStore } from '../../store/appStore';
import { resolveTagMac } from './EntitySelectors';

/**
 * Reactive hook that resolves vehicle/beacon/operator MACs from either the
 * manual inputs or the selected entities, per field independently.
 */
export function useResolvedMacs() {
  const manualVehicle = useAppStore((s) => s.manualVehicle);
  const manualBeacon = useAppStore((s) => s.manualBeacon);
  const manualOperator = useAppStore((s) => s.manualOperator);
  const manualMacVehicle = useAppStore((s) => s.manualMacVehicle);
  const manualMacBeacon = useAppStore((s) => s.manualMacBeacon);
  const manualMacOperator = useAppStore((s) => s.manualMacOperator);
  const vehicle = useAppStore((s) => s.selectedVehicle);
  const beacon = useAppStore((s) => s.selectedBeacon);
  const employee = useAppStore((s) => s.selectedEmployee);

  const up = (s) => (s && s.trim() ? s.trim().toUpperCase() : null);

  // Vehicle MAC
  let macVehicle;
  if (manualVehicle) {
    macVehicle = up(manualMacVehicle);
  } else {
    macVehicle =
      vehicle?.mac?.toUpperCase() ||
      resolveTagMac(vehicle?.smart_flow_tag) ||
      null;
  }

  // Beacon MAC
  let macBeacon;
  if (manualBeacon) {
    macBeacon = up(manualMacBeacon);
  } else {
    macBeacon = beacon?.mac ? beacon.mac.toUpperCase() : null;
  }

  // Operator MAC
  let macOperator;
  if (manualOperator) {
    macOperator = up(manualMacOperator);
  } else {
    macOperator = employee?.mac?.toUpperCase() || null;
    if (!macOperator && employee) {
      for (const t of employee.smart_flow_tags || []) {
        const m = resolveTagMac(t);
        if (m) { macOperator = m; break; }
      }
    }
  }

  return {
    macVehicle,
    macBeacon,
    macOperator,
    vehicle,
    beacon,
    employee,
  };
}
