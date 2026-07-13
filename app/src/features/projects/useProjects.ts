import { useCallback, useEffect, useState } from 'react';

import { errorMessage } from '../../api/errorMessage';
import { listProjects } from './api';

export function useProjects(enabled = true) {
  const [projects, setProjects] = useState<string[]>([]);
  const [loading, setLoading] = useState(enabled);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setProjects(await listProjects());
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (enabled) {
      void refresh();
    }
  }, [enabled, refresh]);

  return { projects, loading, error, refresh };
}
