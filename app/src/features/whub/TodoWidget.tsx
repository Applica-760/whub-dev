import { Alert, Anchor, Badge, Group, Stack, Text } from '@mantine/core';
import { NavLink } from 'react-router';

import { WidgetFrame } from '../../components/WidgetFrame';
import { useTodos } from '../todos/useTodos';

const priorityColor = {
  red: 'red',
  yellow: 'yellow',
  blue: 'blue',
  none: 'gray',
} as const;

export function TodoWidget() {
  const { todos, loading, error } = useTodos();

  return (
    <WidgetFrame
      action={<Anchor component={NavLink} size="sm" to="/todos">すべて表示</Anchor>}
      title="Todo"
    >
      {error && <Alert color="red" title="Todoを取得できませんでした">{error}</Alert>}
      {loading ? (
        <Text c="dimmed">Todoを読み込んでいます…</Text>
      ) : (
        <Stack gap={0}>
          {todos.pending.length === 0 ? (
            <Text c="dimmed" py="md" ta="center">未完了のTodoはありません。</Text>
          ) : (
            todos.pending.map((todo) => (
              <Group className="whub-widget-row" gap="sm" justify="space-between" key={todo.id} wrap="nowrap">
                <div>
                  <Text fw={500}>{todo.title}</Text>
                  {(todo.project || todo.due_date) && (
                    <Text c="dimmed" size="sm">
                      {[todo.project, todo.due_date && `締切 ${todo.due_date}`].filter(Boolean).join(' · ')}
                    </Text>
                  )}
                </div>
                <Badge color={priorityColor[todo.priority]} size="sm" variant="light">
                  {todo.priority}
                </Badge>
              </Group>
            ))
          )}
        </Stack>
      )}
    </WidgetFrame>
  );
}
