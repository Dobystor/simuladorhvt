import { useCallback, useEffect } from 'react';
import apiClient from '../../services/apiClient';
import { useAppStore } from '../../store/appStore';

// Loads entities once (if not already loaded) and exposes a reload function.
export function useEntities() {
  const entities = useAppStore((s) => s.entities);
  const loading = useAppStore((s) => s.entitiesLoading);
  const errors = useAppStore((s) => s.entitiesErrors);
  const setEntities = useAppStore((s) => s.setEntities);
  const setLoading = useAppStore((s) => s.setEntitiesLoading);
  const setErrors = useAppStore((s) => s.setEntitiesErrors);

  const load = useCallback(
    async (force = false) => {
      setLoading(true);
      try {
        const url = force ? '/entities/reload' : '/entities';
        const method = force ? apiClient.post : apiClient.get;
        const res = await method(url);
        const d = res.data;
        setEntities({
          vehicles: d.vehicles || [],
          employees: d.employees || [],
          beacons: d.beacons || [],
          haulageSites: d.haulage_sites || [],
          weighingMachines: d.weighing_machines || [],
        });
        setErrors(d.errors || {});
      } catch (err) {
        setErrors({ _all: err.response?.data?.detail || 'Failed to load entities' });
      } finally {
        setLoading(false);
      }
    },
    [setEntities, setErrors, setLoading]
  );

  useEffect(() => {
    const empty =
      entities.vehicles.length === 0 &&
      entities.beacons.length === 0 &&
      entities.employees.length === 0;
    if (empty) load(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return { entities, loading, errors, reload: () => load(true) };
}
