import { useCallback, useEffect, useState } from "react";

import { errorMessage } from "../../api/errorMessage";
import { listResourceStatus } from "./api";
import type { ResourceStatusItem } from "./api";

export function useResourceStatus() {
  const [resources, setResources] = useState<ResourceStatusItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [updatedAt, setUpdatedAt] = useState<Date | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await listResourceStatus();
      setResources(response.resources);
      setUpdatedAt(new Date());
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return { resources, loading, error, updatedAt, refresh };
}
