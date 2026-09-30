export default function PublishResult({ result }) {
  if (!result) return null;
  return (
    <div className={`notice ${result.ok ? 'ok' : 'err'}`}>{result.message}</div>
  );
}
