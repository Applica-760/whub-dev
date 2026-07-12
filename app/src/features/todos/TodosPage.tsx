import { Alert, Paper, Stack, Text } from '@mantine/core';
import { useState } from 'react';

import { PageFrame } from '../../components/PageFrame';
import { useProjects } from '../projects/useProjects';
import { completeTodo, createTodo, deleteTodo } from './api';
import { TodoForm } from './TodoForm';
import { TodoList } from './TodoList';
import { useTodos } from './useTodos';
import { errorMessage } from '../../api/errorMessage';
import type { TodoCreateInput } from './api';

type Mutation = 'create' | number | null;

export function TodosPage() {
  const { projects, error: projectsError } = useProjects();
  const { todos, loading, error: todosError, refresh } = useTodos();
  const [mutation, setMutation] = useState<Mutation>(null);
  const [mutationError, setMutationError] = useState<string | null>(null);

  async function handleCreate(input: TodoCreateInput): Promise<boolean> {
    setMutation('create');
    setMutationError(null);
    try {
      await createTodo(input);
      await refresh();
      return true;
    } catch (requestError) {
      setMutationError(errorMessage(requestError));
      return false;
    } finally {
      setMutation(null);
    }
  }

  async function handleComplete(todoId: number) {
    if (!window.confirm('このTodoを完了にしますか？')) {
      return;
    }

    setMutation(todoId);
    setMutationError(null);
    try {
      await completeTodo(todoId);
      await refresh();
    } catch (requestError) {
      setMutationError(errorMessage(requestError));
    } finally {
      setMutation(null);
    }
  }

  async function handleDelete(todoId: number) {
    if (!window.confirm('このTodoを削除しますか？')) {
      return;
    }

    setMutation(todoId);
    setMutationError(null);
    try {
      await deleteTodo(todoId);
      await refresh();
    } catch (requestError) {
      setMutationError(errorMessage(requestError));
    } finally {
      setMutation(null);
    }
  }

  return (
    <PageFrame>
      <Stack gap="md">
        <Paper p="md" radius="md" shadow="xs" withBorder>
          <TodoForm
            onCreate={handleCreate}
            projects={projects}
            submitting={mutation === 'create'}
          />
        </Paper>

        {projectsError && <Alert color="red" title="Projectを取得できませんでした">{projectsError}</Alert>}
        {todosError && <Alert color="red" title="Todoを取得できませんでした">{todosError}</Alert>}
        {mutationError && <Alert color="red" title="操作できませんでした">{mutationError}</Alert>}

        {loading ? (
          <Text c="dimmed">Todoを読み込んでいます…</Text>
        ) : (
          <Stack gap="lg">
            <TodoList
              busyTodoId={typeof mutation === 'number' ? mutation : null}
              completed={todos.completed}
              onComplete={(todoId) => void handleComplete(todoId)}
              onDelete={(todoId) => void handleDelete(todoId)}
              pending={todos.pending}
            />
          </Stack>
        )}
      </Stack>
    </PageFrame>
  );
}
