import { useCallback, useEffect, useState } from "react";

import { errorMessage } from "../../api/errorMessage";
import { listTodos } from "./api";
import type { TodoItem } from "./api";

type TodoLists = {
  pending: TodoItem[];
  completed: TodoItem[];
};

export function useTodos() {
  const [todos, setTodos] = useState<TodoLists>({ pending: [], completed: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setTodos(await listTodos());
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return { todos, loading, error, refresh };
}
