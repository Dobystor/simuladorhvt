import { useEffect, useRef, useState } from 'react';

/**
 * A dropdown with a type-to-filter search box, themed for the cyber-dark UI.
 *
 * Props:
 *   - options: array of { value, label }
 *   - value: currently selected value (or '' / null)
 *   - onChange: (value) => void
 *   - placeholder: shown when nothing is selected
 */
export default function SearchableSelect({ options, value, onChange, placeholder = '— Select —' }) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const rootRef = useRef(null);

  const selected = options.find((o) => String(o.value) === String(value));

  const filtered = query.trim()
    ? options.filter((o) => o.label.toLowerCase().includes(query.trim().toLowerCase()))
    : options;

  // Close on outside click.
  useEffect(() => {
    function onDocClick(e) {
      if (rootRef.current && !rootRef.current.contains(e.target)) {
        setOpen(false);
        setQuery('');
      }
    }
    document.addEventListener('mousedown', onDocClick);
    return () => document.removeEventListener('mousedown', onDocClick);
  }, []);

  function pick(opt) {
    onChange(opt.value);
    setOpen(false);
    setQuery('');
  }

  return (
    <div ref={rootRef} style={{ position: 'relative' }}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        style={{
          width: '100%',
          textAlign: 'left',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '9px 11px',
        }}
      >
        <span style={{ color: selected ? 'var(--text)' : 'var(--text-dim)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {selected ? selected.label : placeholder}
        </span>
        <span style={{ color: 'var(--text-dim)', marginLeft: 8 }}>▾</span>
      </button>

      {open && (
        <div
          style={{
            position: 'absolute',
            top: 'calc(100% + 4px)',
            left: 0,
            right: 0,
            zIndex: 50,
            background: 'var(--bg-3)',
            border: '1px solid var(--border-light)',
            borderRadius: 8,
            boxShadow: '0 16px 48px rgba(0,0,0,0.6)',
            overflow: 'hidden',
          }}
        >
          <div style={{ padding: 8, borderBottom: '1px solid var(--border)' }}>
            <input
              autoFocus
              placeholder="Type to search…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </div>
          <div style={{ maxHeight: 240, overflowY: 'auto' }}>
            <div
              onClick={() => pick({ value: '' })}
              style={{ padding: '8px 11px', cursor: 'pointer', color: 'var(--text-dim)', fontSize: 13 }}
            >
              {placeholder}
            </div>
            {filtered.map((o) => (
              <div
                key={o.value}
                onClick={() => pick(o)}
                style={{
                  padding: '8px 11px',
                  cursor: 'pointer',
                  fontSize: 13,
                  background: String(o.value) === String(value) ? 'rgba(91,143,217,0.12)' : 'transparent',
                  color: String(o.value) === String(value) ? 'var(--neon-cyan)' : 'var(--text)',
                }}
                onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(255,255,255,0.05)')}
                onMouseLeave={(e) => (e.currentTarget.style.background = String(o.value) === String(value) ? 'rgba(91,143,217,0.12)' : 'transparent')}
              >
                {o.label}
              </div>
            ))}
            {filtered.length === 0 && (
              <div style={{ padding: '10px 11px', color: 'var(--text-dim)', fontSize: 13 }}>No matches</div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
