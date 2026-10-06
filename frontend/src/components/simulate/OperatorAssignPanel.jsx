import EntitySelectors from './EntitySelectors';
import { useResolvedMacs } from './useResolvedMacs';
import { usePublish } from './usePublish';
import ResultBanner from './ResultBanner';

export default function OperatorAssignPanel({ entities, errors, reload }) {
  const { macVehicle, macOperator, vehicle, employee } = useResolvedMacs();
  const { result, busy, publish } = usePublish();

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
      {vehicle && vehicle.has_tag === false && <div className="error">Vehicle has no addressable MAC.</div>}
      {employee && employee.has_tag === false && <div className="error">Operator has no addressable MAC.</div>}
      <button className="primary" style={{ marginTop: 14 }} disabled={!canPublish} onClick={handlePublish}>
        Publish operator assignment
      </button>
      <ResultBanner result={result} />
    </div>
  );
}
