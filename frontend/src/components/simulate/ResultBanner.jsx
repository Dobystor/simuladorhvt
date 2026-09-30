export default function ResultBanner({ result }) {
  if (!result) return null;
  if (result.ok) {
    return (
      <div className="banner ok">
        Published successfully. Event log #{result.eventLogId}
        {result.eventId ? ` · EventId ${result.eventId}` : ''}
      </div>
    );
  }
  const cls = result.status === 409 ? 'warn' : 'err';
  return <div className={`banner ${cls}`}>{result.message}</div>;
}
