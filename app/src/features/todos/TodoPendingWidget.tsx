import { Alert, Anchor, Text } from '@mantine/core';
import { NavLink } from 'react-router';

import { WidgetFrame } from '../../components/WidgetFrame';
import { TodoList } from './TodoList';
import type { TodoWidgetsController } from './useTodoWidgets';

type TodoPendingWidgetProps = {
  controller: TodoWidgetsController;
  showAllLink?: boolean;
};

export function TodoPendingWidget({
  controller,
  showAllLink = false,
}: TodoPendingWidgetProps) {
  const action = showAllLink
    ? <Anchor component={NavLink} size="sm" to="/todos">すべて表示</Anchor>
    : undefined;

  return (
    <WidgetFrame
      action={action}
      title={<Text c="dimmed" fw={600} size="sm" tt="uppercase">これからやる</Text>}
    >
      {controller.todosError && (
        <Alert color="red" title="Todoを取得できませんでした">{controller.todosError}</Alert>
      )}
      {controller.listError && (
        <Alert color="red" title="操作できませんでした">{controller.listError}</Alert>
      )}
      {controller.loading ? (
        <Text c="dimmed" p="md">Todoを読み込んでいます…</Text>
      ) : (
        <TodoList
          busyTodoId={typeof controller.mutation === 'number' ? controller.mutation : null}
          emptyMessage="これからやるTodoはありません"
          onComplete={(todoId) => void controller.handleComplete(todoId)}
          onDelete={(todoId) => void controller.handleDelete(todoId)}
          todos={controller.todos.pending}
        />
      )}
    </WidgetFrame>
  );
}
