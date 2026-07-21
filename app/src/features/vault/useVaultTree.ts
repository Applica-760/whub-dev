import { useCallback, useEffect, useState } from "react";

import type { VaultNode } from "../../api/client";
import { errorMessage } from "../../api/errorMessage";
import { fetchVaultTree } from "./api";

export function useVaultTree() {
  const [nodes, setNodes] = useState<VaultNode[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setNodes(await fetchVaultTree());
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return { nodes, loading, error, refresh };
}
