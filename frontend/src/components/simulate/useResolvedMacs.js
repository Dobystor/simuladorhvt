import { useAppStore } from '../../store/appStore';
import { resolveTagMac } from './EntitySelectors';

/**
 * Reactive hook that resolves vehicle/beacon/operator MACs from either the
 * manual inputs or the selected entities. Re-renders when any relevant piece of
 * state changes, so Publish buttons enable/disable correctly.
 */
export function useResolvedMacs() {
  const manualMode = useAppStore((s) => s.manualMacEntry);
  const manualMacVehicle = useAppStore((s) => s.manualMacVehicle);
  const manualMacBeacon = useAppStore((s) => s.manualMacBeacon);
  const manualMacOperator = useAppStore((s) => s.manualMacOperator);
  const vehicle = useAppStore((s) => s.selectedVehicle);
  const beacon = useAppStore((s) => s.selectedBeacon);
  const employee = useAppStore((s) => s.selectedEmployee);

  const up = (s) => (s && s.trim() ? s.trim().toUpperCase() : null);

  if (manualMode) {
    return {
      macVehicle: up(manualMacVehicle),
      macBeacon: up(manualMacBeacon),
      macOperator: up(manualMacOperator),
      vehicle,
      beacon,
      employee,
      manualMode,
    };
  }

  const macVehicle =
    vehicle?.mac?.toUpperCase() ||
    vehicle?.mac_vehicle?.toUpperCase() ||
    resolveTagMac(vehicle?.smart_flow_tag) ||
    null;

  let macOperator = employee?.mac?.toUpperCase() || null;
  if (!macOperator && employee) {
    for (const t of employee.smart_flow_tags || []) {
      const m = resolveTagMac(t);
      if (m) { macOperator = m; break; }
    }
  }

  return {
    macVehicle,
    macBeacon: beacon?.mac ? beacon.mac.toUpperCase() : null,
    macOperator,
    vehicle,
    beacon,
    employee,
    manualMode,
  };
}
