import { useState } from 'react';
import apiClient from '../../services/apiClient';

// Shared publish helper returning a normalized result object.
export function usePublish() {
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);

  async function publish(path, body) {
    setBusy(true);
    setResult(null);
    try {
      const res = await apiClient.post(path, body);
      const r = {
        ok: true,
        eventLogId: res.data.event_log_id,
        eventId: res.data.event_id,
      };
      setResult(r);
      return r;
    } catch (err) {
      const r = {
        ok: false,
        status: err.response?.status,
        message: err.response?.data?.detail || 'Publish failed',
      };
      setResult(r);
      return r;
    } finally {
      setBusy(false);
    }
  }

  return { result, busy, publish, setResult };
}
