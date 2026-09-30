import { useState } from 'react';
import { useEntities } from '../components/simulate/useEntities';
import ModeSelector from '../components/simulate/ModeSelector';
import LoadPanel from '../components/simulate/LoadPanel';
import UnloadPanel from '../components/simulate/UnloadPanel';
import WeighingPanel from '../components/simulate/WeighingPanel';
import InTransitStopPanel from '../components/simulate/InTransitStopPanel';
import LocationUnloadPanel from '../components/simulate/LocationUnloadPanel';
import OperatorAssignPanel from '../components/simulate/OperatorAssignPanel';

const TABS = [
  { key: 'Load', label: 'Load', mode: true },
  { key: 'Unload', label: 'Unload', mode: true },
  { key: 'WeighingMachine', label: 'Weighing', mode: true },
  { key: 'InTransitStop', label: 'InTransit / Stop', mode: true },
  { key: 'LocationUnload', label: 'Location Unload', mode: false },
  { key: 'OperatorAssign', label: 'Operator Assign', mode: false },
];

export default function SimulatePage() {
  const [tab, setTab] = useState('Load');
  const { entities, loading, errors, reload } = useEntities();

  const active = TABS.find((t) => t.key === tab);
  const props = { entities, errors, reload };

  return (
    <div>
      <h2>Simulate events</h2>
      {loading && <p className="muted">Loading entities…</p>}

      <div className="tabs">
        {TABS.map((t) => (
          <button
            key={t.key}
            className={`tab ${tab === t.key ? 'active' : ''}`}
            onClick={() => setTab(t.key)}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="panel">
        {active.mode && (
          <div style={{ marginBottom: 18 }}>
            <ModeSelector />
          </div>
        )}

        {tab === 'Load' && <LoadPanel {...props} />}
        {tab === 'Unload' && <UnloadPanel {...props} />}
        {tab === 'WeighingMachine' && <WeighingPanel {...props} />}
        {tab === 'InTransitStop' && <InTransitStopPanel {...props} />}
        {tab === 'LocationUnload' && <LocationUnloadPanel {...props} />}
        {tab === 'OperatorAssign' && <OperatorAssignPanel {...props} />}
      </div>
    </div>
  );
}
