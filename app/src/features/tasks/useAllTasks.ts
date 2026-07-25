import { useCallback, useEffect, useRef, useState } from "react";

import { errorMessage } from "../../api/errorMessage";
import { listAllTasks } from "./api";
import type { TaskSummary } from "./useTasks";

export type ProjectTaskSummary = TaskSummary & { project: string };

export type ProjectTaskError = { project: string; error: string };

export function useAllTasks() {
  const [tasks, setTasks] = useState<ProjectTaskSummary[]>([]);
  const [projectErrors, setProjectErrors] = useState<ProjectTaskError[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const requestId = useRef(0);

  const refresh = useCallback(async () => {
    const currentRequest = ++requestId.current;
    setLoading(true);
    setError(null);
    try {
      const response = await listAllTasks();
      if (currentRequest !== requestId.current) {
        return;
      }
      setTasks(
        response.projects.flatMap((entry) =>
          entry.tasks.map((task) => ({ ...task, project: entry.project })),
        ),
      );
      // Project単位の失敗は他Projectの描画を止めず、警告として保持する
      setProjectErrors(
        response.projects.flatMap((entry) =>
          entry.error ? [{ project: entry.project, error: entry.error }] : [],
        ),
      );
    } catch (requestError) {
      if (currentRequest === requestId.current) {
        setTasks([]);
        setProjectErrors([]);
        setError(errorMessage(requestError));
      }
    } finally {
      if (currentRequest === requestId.current) {
        setLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    void refresh();
    return () => {
      requestId.current += 1;
    };
  }, [refresh]);

  return { tasks, projectErrors, loading, error, refresh };
}
