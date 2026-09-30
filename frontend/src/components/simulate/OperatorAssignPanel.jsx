import { useAppStore } from '../../store/appStore';
import EntitySelectors, { vehicleMac, employeeMac } from './EntitySelectors';
import { usePublish } from './usePublish';
import ResultBanner from './ResultBanner';

export default function OperatorAssignPanel({ entities, errors, reload }) {
  const vehicle = useAppStore((s) => s.selectedVehicle);
  const employee = useAppStore((s) => s.selectedEmployee);
  const { result, busy, publish } = usePublish();

  const macVehicle = vehicleMac(vehicle);
  const macOperator = employeeMac(employee);
  const canPublish = macVehicle && macOperator && !busy;

  async function handlePublish() {
    await publish('/simulate/operator-assign', {
      mac_vehicle: macVehicle,
      mac_operator: macOperator,
    });
  }

  return (
    <div>
      <EntitySelectors entities={entities} errors={errors} reload={reload} showBeacon={false} />
      {vehicle && !macVehicle && <div className="error">Vehicle has no addressable MAC.</div>}
      {employee && !macOperator && <div className="error">Operator has no addressable MAC.</div>}
      <button className="primary" style={{ marginTop: 14 }} disabled={!canPublish} onClick={handlePublish}>
        Publish operator assignment
      </button>
      <ResultBanner result={result} />
    </div>
  );
}
