import { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import apiClient from '../../services/apiClient';
import { useAppStore } from '../../store/appStore';
import ModeSelector from './ModeSelector';
import EntitySelectors from './EntitySelectors';
import LoadPanel from './LoadPanel';
import UnloadPanel from './UnloadPanel';
import WeighingPanel from './WeighingPanel';
import InTransitStopPanel from './InTransitStopPanel';
import LocationUnloadPanel from './LocationUnloadPanel';
import OperatorAssignPanel from './OperatorAssignPanel';

const TABS = [
  { key: 'Load', label: 'Load' },
  { key: 'Unload', label: 'Unload' },
  { key: 'WeighingMachine', label: 'Weighing' },
  { key: 'InTransitStop', label: 'InTransit / Stop' },
  { key: 'LocationUnload', label: 'Location Unload' },
  { key: 'OperatorAssign', label: 'Operator Assign' },
];

export default function SimulatePage() {
  const location = useLocation();
  const [tab, setTab] = useState('Load');
  const entities = useAppStore((s) => s.entities);
  const setEntities = useAppStore((s) => s.setEntities);
  const setEntitiesLoading = useAppStore((s) => s.setEntitiesLoading);
  const entitiesLoading = useAppStore((s) => s.entitiesLoading);

  const loadEntities = async (reload = false) => {
    setEntitiesLoading(true);
    try {
      const url = reload ? '/entities/reload' : '/entities';
      const resp = await (reload ? apiClient.post(url) : apiClient.get(url));
      setEntities(
        {
          vehicles: resp.data.vehicles,
          employees: resp.data.employees,
          beacons: resp.data.beacons,
          haulageSites: resp.data.haulage_sites,
          weighingMachines: resp.data.weighing_machines,
        },
        resp.data.errors || {}
      );
    } catch {
      setEntitiesLoading(false);
    }
  };

  useEffect(() => {
    if (!entities.vehicles.length) loadEntities(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const panelProps = { prefillMac: location.state?.macVehicle };

  return (
    <div>
      <h2>Simulate Events</h2>
      <div className="tabs">
        {TABS.map((t) => (
          <div
            key={t.key}
            className={`tab ${tab === t.key ? 'active' : ''}`}
            onClick={() => setTab(t.key)}
          >
            {t.label}
          </div>
        ))}
      </div>

      <div className="card">
        <div className="row" style={{ justifyContent: 'space-between' }}>
          <span className="muted">
            {entitiesLoading ? 'Loading entities…' : 'Entities loaded'}
          </span>
          <button className="secondary" onClick={() => loadEntities(true)}>
            Reload entities
          </button>
        </div>
      </div>

      {tab === 'Load' && (
        <>
          <ModeSelector />
          <EntitySelectors beaconType="Load" />
          <LoadPanel {...panelProps} />
        </>
      )}
      {tab === 'Unload' && (
        <>
          <ModeSelector />
          <EntitySelectors beaconType="Unload" />
          <UnloadPanel {...panelProps} />
        </>
      )}
      {tab === 'WeighingMachine' && (
        <>
          <ModeSelector />
          <EntitySelectors beaconType="Weighing" />
          <WeighingPanel {...panelProps} />
        </>
      )}
      {tab === 'InTransitStop' && (
        <>
          <ModeSelector />
          <EntitySelectors beaconType="none" />
          <InTransitStopPanel {...panelProps} />
        </>
      )}
      {tab === 'LocationUnload' && <LocationUnloadPanel {...panelProps} />}
      {tab === 'OperatorAssign' && (
        <>
          <EntitySelectors beaconType="none" showEmployee />
          <OperatorAssignPanel {...panelProps} />
        </>
      )}
    </div>
  );
}
