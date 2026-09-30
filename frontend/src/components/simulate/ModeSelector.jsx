import { useAppStore } from '../../store/appStore';
import DateTimePicker from '../DateTimePicker';

export default function ModeSelector() {
  const mode = useAppStore((s) => s.simulationMode);
  const dateStatus = useAppStore((s) => s.dateStatusInput);
  const setField = useAppStore((s) => s.setSimulationFormField);

  return (
    <div className="row" style={{ alignItems: 'flex-end' }}>
      <div className="col" style={{ maxWidth: 240 }}>
        <label>Mode</label>
        <div style={{ display: 'flex', gap: 12 }}>
          <label style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
            <input
              type="radio"
              name="mode"
              checked={mode === 'Online'}
              onChange={() => setField('simulationMode', 'Online')}
              style={{ width: 'auto' }}
            />
            Online (now)
          </label>
          <label style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
            <input
              type="radio"
              name="mode"
              checked={mode === 'Offline'}
              onChange={() => setField('simulationMode', 'Offline')}
              style={{ width: 'auto' }}
            />
            Offline (past)
          </label>
        </div>
      </div>
      <div className="col" style={{ maxWidth: 280 }}>
        <label>DateStatus (past)</label>
        <DateTimePicker
          disabled={mode !== 'Offline'}
          value={dateStatus}
          onChange={(iso) => setField('dateStatusInput', iso)}
        />
      </div>
    </div>
  );
}

// Returns { mode, dateStatusIso, valid, reason } for the current form state.
export function useModeValidation() {
  const mode = useAppStore((s) => s.simulationMode);
  const dateStatus = useAppStore((s) => s.dateStatusInput);

  if (!mode) return { mode: null, valid: false, reason: 'Select a mode' };
  if (mode === 'Online') return { mode, dateStatusIso: null, valid: true };

  // Offline: dateStatus is already an ISO 8601 string from the picker.
  if (!dateStatus) return { mode, valid: false, reason: 'Provide a past DateStatus' };
  const dt = new Date(dateStatus);
  if (Number.isNaN(dt.getTime())) return { mode, valid: false, reason: 'Invalid date' };
  if (dt.getTime() >= Date.now()) {
    return { mode, valid: false, reason: 'DateStatus must be strictly in the past' };
  }
  return { mode, dateStatusIso: dateStatus, valid: true };
}
