import { useCallback, useEffect, useRef, useState } from "react";

import { errorMessage } from "../../api/errorMessage";
import { listTasks } from "./api";
import type { TasksResponse } from "../../api/client";

export type TaskSummary = TasksResponse["tasks"][number];

export function useTasks(project?: string | null) {
  const [tasks, setTasks] = useState<TaskSummary[]>([]);
  const [loading, setLoading] = useState(project !== null);
  const [error, setError] = useState<string | null>(null);
  const requestId = useRef(0);

  const refresh = useCallback(async () => {
    const currentRequest = ++requestId.current;
    if (project === null) {
      setTasks([]);
      setLoading(false);
      setError(null);
      return;
    }

    setLoading(true);
    setError(null);
    setTasks([]);
    try {
      const response = await listTasks(project);
      if (currentRequest === requestId.current) {
        setTasks(response.tasks);
      }
    } catch (requestError) {
      if (currentRequest === requestId.current) {
        setError(errorMessage(requestError));
      }
    } finally {
      if (currentRequest === requestId.current) {
        setLoading(false);
      }
    }
  }, [project]);

  useEffect(() => {
    void refresh();
    return () => {
      requestId.current += 1;
    };
  }, [refresh]);

  return { tasks, loading, error, refresh };
}
