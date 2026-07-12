import { Text } from '@mantine/core';

import { WidgetFrame } from '../../components/WidgetFrame';
import { TodoList } from './TodoList';
import type { TodoWidgetsController } from './useTodoWidgets';

type TodoCompletedWidgetProps = {
  controller: TodoWidgetsController;
};

export function TodoCompletedWidget({ controller }: TodoCompletedWidgetProps) {
  return (
    <WidgetFrame
      title={(
        <Text c="dimmed" fw={600} size="sm">
          完了済み ({controller.todos.completed.length})
        </Text>
      )}
    >
      {controller.loading ? (
        <Text c="dimmed" p="md">Todoを読み込んでいます…</Text>
      ) : (
        <TodoList
          busyTodoId={typeof controller.mutation === 'number' ? controller.mutation : null}
          completed
          emptyMessage="完了済みのTodoはありません"
          onComplete={(todoId) => void controller.handleComplete(todoId)}
          onDelete={(todoId) => void controller.handleDelete(todoId)}
          todos={controller.todos.completed}
        />
      )}
    </WidgetFrame>
  );
}
