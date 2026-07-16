import { useCallback, useEffect, useState } from 'react';

import { errorMessage } from '../../api/errorMessage';
import { listTasks } from './api';
import type { TasksResponse } from '../../api/client';

export type TaskSummary = TasksResponse['tasks'][number];

export function useTasks() {
  const [tasks, setTasks] = useState<TaskSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setTasks((await listTasks()).tasks);
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return { tasks, loading, error, refresh };
}
