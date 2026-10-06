import { useModeValidation } from './ModeSelector';
import EntitySelectors from './EntitySelectors';
import { useResolvedMacs } from './useResolvedMacs';
import { usePublish } from './usePublish';
import ResultBanner from './ResultBanner';

export default function InTransitStopPanel({ entities, errors, reload }) {
  const { macVehicle, vehicle } = useResolvedMacs();
  const mode = useModeValidation();
  const { result, busy, publish } = usePublish();

  async function emit(eventType) {
    if (!macVehicle) return;
    await publish('/simulate/haulage', {
      event_type: eventType,
      mac_vehicle: macVehicle,
      mode: mode.mode,
      date_status: mode.dateStatusIso,
    });
  }

  const disabled = !macVehicle || !mode.valid || busy;

  return (
    <div>
      <EntitySelectors
        entities={entities}
        errors={errors}
        reload={reload}
        showBeacon={false}
        showEmployee={false}
      />
      {vehicle && vehicle.has_tag === false && (
        <div className="error">Selected vehicle has no addressable tag.</div>
      )}
      {!macVehicle && <div className="muted" style={{ marginTop: 8 }}>Select a vehicle or enter a MAC.</div>}
      <div style={{ display: 'flex', gap: 10, marginTop: 14 }}>
        <button className="primary" disabled={disabled} onClick={() => emit('InTransit')}>
          Publish InTransit
        </button>
        <button className="primary" disabled={disabled} onClick={() => emit('Stop')}>
          Publish Stop
        </button>
      </div>
      <ResultBanner result={result} />
    </div>
  );
}
