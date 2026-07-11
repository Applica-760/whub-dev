import {
  Alert,
  Button,
  Group,
  Paper,
  Radio,
  Select,
  Stack,
  Text,
  TextInput,
} from '@mantine/core';
import { useCallback, useEffect, useState } from 'react';
import type { FormEvent } from 'react';

import { requestJson } from '../../api/client';
import type { components } from '../../api/generated/schema';
import { PageFrame } from '../../components/PageFrame';
import { TodoList, type TodoItem } from './TodoList';

type TodoListResponse = components['schemas']['TodoListResponse'];
type Priority = components['schemas']['CreateTodoRequest']['priority'];
type Mutation = 'create' | number | null;

const priorityOptions = [
  { value: 'none', color: 'gray' },
  { value: 'red', color: 'red' },
  { value: 'yellow', color: 'yellow' },
  { value: 'blue', color: 'blue' },
] as const;

export function TodosPage() {
  const [todos, setTodos] = useState<TodoListResponse>({ pending: [], completed: [] });
  const [projects, setProjects] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [mutation, setMutation] = useState<Mutation>(null);
  const [title, setTitle] = useState('');
  const [project, setProject] = useState<string | null>(null);
  const [priority, setPriority] = useState<Priority>('none');
  const [dueDate, setDueDate] = useState('');

  const refreshTodos = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await requestJson<TodoListResponse>('/api/todos');
      setTodos(response);
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setLoading(false);
    }
  }, []);

  const loadProjects = useCallback(async () => {
    try {
      const response = await requestJson<components['schemas']['ProjectsResponse']>('/api/projects');
      setProjects(response.projects);
    } catch (requestError) {
      setError(errorMessage(requestError));
    }
  }, []);

  useEffect(() => {
    void refreshTodos();
    void loadProjects();
  }, [loadProjects, refreshTodos]);

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalizedTitle = title.trim();
    if (!normalizedTitle) {
      return;
    }

    setMutation('create');
    setError(null);
    try {
      await requestJson<TodoItem>('/api/todos', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: normalizedTitle,
          project,
          priority,
          due_date: dueDate || null,
        }),
      });
      setTitle('');
      setProject(null);
      setPriority('none');
      setDueDate('');
      await refreshTodos();
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setMutation(null);
    }
  }

  async function handleComplete(todoId: number) {
    if (!window.confirm('このTodoを完了にしますか？')) {
      return;
    }

    setMutation(todoId);
    setError(null);
    try {
      await requestJson<TodoItem>(`/api/todos/${todoId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ done: true }),
      });
      await refreshTodos();
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setMutation(null);
    }
  }

  async function handleDelete(todoId: number) {
    if (!window.confirm('このTodoを削除しますか？')) {
      return;
    }

    setMutation(todoId);
    setError(null);
    try {
      await requestJson<void>(`/api/todos/${todoId}`, { method: 'DELETE' });
      await refreshTodos();
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setMutation(null);
    }
  }

  return (
    <PageFrame>
      <Stack gap="md">
        <Paper p="md" radius="md" shadow="xs" withBorder>
          <form onSubmit={handleCreate}>
            <Stack gap="sm">
              <Group align="end" wrap="nowrap">
                <TextInput
                  aria-label="Todoのタイトル"
                  disabled={mutation !== null}
                  flex={1}
                  onChange={(event) => setTitle(event.currentTarget.value)}
                  placeholder="次にすること"
                  required
                  value={title}
                />
                <Button loading={mutation === 'create'} type="submit">
                  追加
                </Button>
              </Group>
              <Group align="end" grow>
                <Select
                  clearable
                  data={projects}
                  label="Project"
                  onChange={setProject}
                  placeholder="指定なし"
                  value={project}
                />
                <Radio.Group
                  label="優先度"
                  onChange={(value) => setPriority(value as Priority)}
                  value={priority}
                >
                  <Group gap="sm" mt="xs">
                    {priorityOptions.map((option) => (
                      <Radio
                        aria-label={option.value}
                        color={option.color}
                        key={option.value}
                        value={option.value}
                      />
                    ))}
                  </Group>
                </Radio.Group>
                <TextInput
                  label="期限"
                  onChange={(event) => setDueDate(event.currentTarget.value)}
                  type="date"
                  value={dueDate}
                />
              </Group>
            </Stack>
          </form>
        </Paper>

        {error && <Alert color="red" title="操作できませんでした">{error}</Alert>}

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

function errorMessage(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }
  return '予期しないエラーが発生しました';
}
