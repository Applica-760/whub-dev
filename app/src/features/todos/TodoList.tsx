import { ActionIcon, Badge, Checkbox, Group, Stack, Text } from '@mantine/core';

import { GroupedListRow, GroupedListSection } from '../../components/GroupedList';
import type { TodoItem } from './api';

export type { TodoItem } from './api';

type TodoListProps = {
  pending: TodoItem[];
  completed: TodoItem[];
  busyTodoId: number | null;
  onComplete: (todoId: number) => void;
  onDelete: (todoId: number) => void;
};

const priorityColor = {
  red: 'red',
  yellow: 'yellow',
  blue: 'blue',
  none: 'gray',
} as const;

const priorityLabel = {
  red: 'red',
  yellow: 'yellow',
  blue: 'blue',
  none: 'none',
} as const;

export function TodoList({
  pending,
  completed,
  busyTodoId,
  onComplete,
  onDelete,
}: TodoListProps) {
  return (
    <>
      <GroupedListSection title="これからやる">
        {pending.length === 0 ? (
          <Text c="dimmed" p="md" ta="center">
            これからやるTodoはありません
          </Text>
        ) : (
          pending.map((todo) => (
            <TodoRow
              key={todo.id}
              todo={todo}
              busy={busyTodoId === todo.id}
              onComplete={onComplete}
              onDelete={onDelete}
            />
          ))
        )}
      </GroupedListSection>

      <GroupedListSection title={`完了済み (${completed.length})`}>
        {completed.length === 0 ? (
          <Text c="dimmed" p="md" ta="center">
            完了済みのTodoはありません
          </Text>
        ) : (
          completed.map((todo) => (
            <TodoRow
              completed
              key={todo.id}
              todo={todo}
              busy={busyTodoId === todo.id}
              onComplete={onComplete}
              onDelete={onDelete}
            />
          ))
        )}
      </GroupedListSection>
    </>
  );
}

type TodoRowProps = {
  todo: TodoItem;
  busy: boolean;
  completed?: boolean;
  onComplete: (todoId: number) => void;
  onDelete: (todoId: number) => void;
};

function TodoRow({
  todo,
  busy,
  completed = false,
  onComplete,
  onDelete,
}: TodoRowProps) {
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
              {priorityLabel[todo.priority]}
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
