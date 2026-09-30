import { useEffect, useRef } from 'react';
import flatpickr from 'flatpickr';
import { Spanish } from 'flatpickr/dist/l10n/es.js';
import 'flatpickr/dist/flatpickr.min.css';
import 'flatpickr/dist/themes/dark.css';

/**
 * A themed datetime picker matching the SmartFlow bot's Flatpickr setup.
 * Emits an ISO 8601 string (with timezone) via onChange, or null when cleared.
 *
 * Props:
 *   - value: ISO string or null
 *   - onChange: (isoString | null) => void
 *   - disabled: bool
 *   - placeholder: string
 */
export default function DateTimePicker({ value, onChange, disabled = false, placeholder = 'Selecciona fecha y hora' }) {
  const inputRef = useRef(null);
  const fpRef = useRef(null);
  const onChangeRef = useRef(onChange);
  onChangeRef.current = onChange;

  useEffect(() => {
    if (!inputRef.current) return;
    fpRef.current = flatpickr(inputRef.current, {
      enableTime: true,
      dateFormat: 'Z',        // real value = ISO 8601 with timezone
      altInput: true,          // show a friendly format to the user
      altFormat: 'd/m/Y H:i',
      time_24hr: true,
      locale: Spanish,
      disableMobile: true,
      minuteIncrement: 1,
      onChange: (dates) => {
        const iso = dates.length > 0 ? dates[0].toISOString() : null;
        onChangeRef.current?.(iso);
      },
    });
    return () => {
      fpRef.current?.destroy();
      fpRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Keep flatpickr in sync when the value is cleared externally.
  useEffect(() => {
    if (!fpRef.current) return;
    if (!value) {
      fpRef.current.clear();
    }
  }, [value]);

  // Toggle the alt input's disabled state (flatpickr creates a sibling input).
  useEffect(() => {
    const alt = fpRef.current?.altInput;
    if (alt) alt.disabled = disabled;
  }, [disabled]);

  return <input ref={inputRef} type="text" placeholder={placeholder} disabled={disabled} />;
}
