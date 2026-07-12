import { ActionIcon, Badge, Checkbox, Group, Stack, Text } from '@mantine/core';

import { GroupedListRow } from '../../components/GroupedList';
import type { TodoItem } from './api';

type TodoListProps = {
  todos: TodoItem[];
  busyTodoId: number | null;
  completed?: boolean;
  emptyMessage: string;
  onComplete: (todoId: number) => void;
  onDelete: (todoId: number) => void;
};

const priorityColor = {
  red: 'red',
  yellow: 'yellow',
  blue: 'blue',
  none: 'gray',
} as const;

export function TodoList({
  todos,
  busyTodoId,
  completed = false,
  emptyMessage,
  onComplete,
  onDelete,
}: TodoListProps) {
  if (todos.length === 0) {
    return <Text c="dimmed" p="md" ta="center">{emptyMessage}</Text>;
  }

  return todos.map((todo) => (
    <TodoRow
      busy={busyTodoId === todo.id}
      completed={completed}
      key={todo.id}
      onComplete={onComplete}
      onDelete={onDelete}
      todo={todo}
    />
  ));
}

type TodoRowProps = {
  todo: TodoItem;
  busy: boolean;
  completed: boolean;
  onComplete: (todoId: number) => void;
  onDelete: (todoId: number) => void;
};

function TodoRow({ todo, busy, completed, onComplete, onDelete }: TodoRowProps) {
  const subtitle = [todo.project, !completed && todo.due_date && `締切 ${todo.due_date}`]
    .filter(Boolean)
    .join(' · ');

  return (
    <GroupedListRow
      leftSection={
        <Checkbox
          aria-label={`${todo.title}を完了にする`}
          checked={completed}
          disabled={busy || completed}
          onChange={() => onComplete(todo.id)}
        />
      }
      rightSection={
        <Group gap={4} wrap="nowrap">
          {completed ? (
            <Stack align="flex-end" gap={0}>
              {todo.done_at && <Text size="sm">完了 {todo.done_at}</Text>}
              {todo.due_date && <Text c="dimmed" size="sm">締切 {todo.due_date}</Text>}
            </Stack>
          ) : (
            <Badge color={priorityColor[todo.priority]} size="sm" variant="light">
              {todo.priority}
            </Badge>
          )}
          <ActionIcon
            aria-label={`${todo.title}を削除する`}
            color="red"
            disabled={busy}
            onClick={() => onDelete(todo.id)}
            variant="subtle"
          >
            ×
          </ActionIcon>
        </Group>
      }
      subtitle={subtitle || undefined}
      title={todo.title}
    />
  );
}
