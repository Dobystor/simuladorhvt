import { useModeValidation } from './ModeSelector';
import EntitySelectors from './EntitySelectors';
import { useResolvedMacs } from './useResolvedMacs';
import { usePublish } from './usePublish';
import ResultBanner from './ResultBanner';

export default function LoadPanel({ entities, errors, reload }) {
  const { macVehicle, macBeacon, macOperator, vehicle } = useResolvedMacs();
  const mode = useModeValidation();
  const { result, busy, publish } = usePublish();

  const canPublish = macVehicle && macBeacon && mode.valid && !busy;

  async function handlePublish() {
    await publish('/simulate/haulage', {
      event_type: 'Load',
      mac_vehicle: macVehicle,
      mac_beacon: macBeacon,
      mac_operator: macOperator,
      mode: mode.mode,
      date_status: mode.dateStatusIso,
    });
  }

  return (
    <div>
      <EntitySelectors entities={entities} errors={errors} reload={reload} />
      {vehicle && vehicle.has_tag === false && (
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
