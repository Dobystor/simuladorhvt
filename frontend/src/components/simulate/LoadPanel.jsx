import { useAppStore } from '../../store/appStore';
import { useModeValidation } from './ModeSelector';
import EntitySelectors, { vehicleMac, employeeMac } from './EntitySelectors';
import { usePublish } from './usePublish';
import ResultBanner from './ResultBanner';

export default function LoadPanel({ entities, errors, reload }) {
  const vehicle = useAppStore((s) => s.selectedVehicle);
  const beacon = useAppStore((s) => s.selectedBeacon);
  const employee = useAppStore((s) => s.selectedEmployee);
  const mode = useModeValidation();
  const { result, busy, publish } = usePublish();

  const macVehicle = vehicleMac(vehicle);
  const canPublish = macVehicle && beacon && mode.valid && !busy;

  async function handlePublish() {
    await publish('/simulate/haulage', {
      event_type: 'Load',
      mac_vehicle: macVehicle,
      mac_beacon: beacon.mac.toUpperCase(),
      mac_operator: employeeMac(employee),
      mode: mode.mode,
      date_status: mode.dateStatusIso,
    });
  }

  return (
    <div>
      <EntitySelectors entities={entities} errors={errors} reload={reload} />
      {vehicle && !macVehicle && (
        <div className="error">Selected vehicle has no addressable tag.</div>
      )}
      {!mode.valid && mode.reason && <div className="muted" style={{ marginTop: 8 }}>{mode.reason}</div>}
      <button className="primary" style={{ marginTop: 14 }} disabled={!canPublish} onClick={handlePublish}>
        Publish Load event
      </button>
      <ResultBanner result={result} />
    </div>
  );
}
