import { useAppStore } from '../../store/appStore';
import { useModeValidation } from './ModeSelector';
import EntitySelectors, { vehicleMac } from './EntitySelectors';
import { usePublish } from './usePublish';
import ResultBanner from './ResultBanner';

export default function InTransitStopPanel({ entities, errors, reload }) {
  const vehicle = useAppStore((s) => s.selectedVehicle);
  const mode = useModeValidation();
  const { result, busy, publish } = usePublish();

  const macVehicle = vehicleMac(vehicle);

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
      {vehicle && !macVehicle && (
        <div className="error">Selected vehicle has no addressable tag.</div>
      )}
      {!vehicle && <div className="muted" style={{ marginTop: 8 }}>Select a vehicle first.</div>}
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
