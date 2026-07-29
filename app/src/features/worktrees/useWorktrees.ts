import { useCallback, useEffect, useState } from "react";

import { errorMessage } from "../../api/errorMessage";
import { listWorktrees } from "./api";
import type { WorktreeItem } from "./api";

export function useWorktrees() {
  const [worktrees, setWorktrees] = useState<WorktreeItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await listWorktrees();
      setWorktrees(response.worktrees);
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return { error, loading, refresh, worktrees };
}
