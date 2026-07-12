import { Alert, Box, Text } from '@mantine/core';

import { WidgetFrame } from '../../components/WidgetFrame';
import { TodoForm } from './TodoForm';
import type { TodoWidgetsController } from './useTodoWidgets';

type TodoFormWidgetProps = {
  controller: TodoWidgetsController;
};

export function TodoFormWidget({ controller }: TodoFormWidgetProps) {
  return (
    <WidgetFrame
      title={<Text c="dimmed" fw={600} size="sm" tt="uppercase">Todoを追加</Text>}
    >
      <Box p="md">
        {controller.projectsError && (
          <Alert color="red" mb="md" title="Projectを取得できませんでした">{controller.projectsError}</Alert>
        )}
        {controller.formError && (
          <Alert color="red" mb="md" title="操作できませんでした">{controller.formError}</Alert>
        )}
        <TodoForm
          onCreate={controller.handleCreate}
          projects={controller.projects}
          submitting={controller.mutation === 'create'}
        />
      </Box>
    </WidgetFrame>
  );
}
