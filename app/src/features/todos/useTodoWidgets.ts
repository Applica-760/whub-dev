import { useState } from "react";

import { errorMessage } from "../../api/errorMessage";
import { useProjects } from "../projects/useProjects";
import { completeTodo, createTodo, deleteTodo } from "./api";
import { useTodos } from "./useTodos";
import type { TodoCreateInput } from "./api";

type Mutation = "create" | number | null;

type UseTodoWidgetsOptions = {
  withForm?: boolean;
};

export function useTodoWidgets({
  withForm = true,
}: UseTodoWidgetsOptions = {}) {
  const { projects, error: projectsError } = useProjects(withForm);
  const { todos, loading, error: todosError, refresh } = useTodos();
  const [mutation, setMutation] = useState<Mutation>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [listError, setListError] = useState<string | null>(null);

  async function handleCreate(input: TodoCreateInput): Promise<boolean> {
    setMutation("create");
    setFormError(null);
    try {
      await createTodo(input);
      await refresh();
      return true;
    } catch (requestError) {
      setFormError(errorMessage(requestError));
      return false;
    } finally {
      setMutation(null);
    }
  }

  async function handleComplete(todoId: number) {
    if (!window.confirm("このTodoを完了にしますか？")) {
      return;
    }
    setMutation(todoId);
    setListError(null);
    try {
      await completeTodo(todoId);
      await refresh();
    } catch (requestError) {
      setListError(errorMessage(requestError));
    } finally {
      setMutation(null);
    }
  }

  async function handleDelete(todoId: number) {
    if (!window.confirm("このTodoを削除しますか？")) {
      return;
    }
    setMutation(todoId);
    setListError(null);
    try {
      await deleteTodo(todoId);
      await refresh();
    } catch (requestError) {
      setListError(errorMessage(requestError));
    } finally {
      setMutation(null);
    }
  }

  return {
    projects,
    projectsError,
    todos,
    loading,
    todosError,
    mutation,
    formError,
    listError,
    handleCreate,
    handleComplete,
    handleDelete,
  };
}

export type TodoWidgetsController = ReturnType<typeof useTodoWidgets>;
