import { Stack } from '@mantine/core';

import { PageFrame } from '../../components/PageFrame';
import { TodoCompletedWidget } from './TodoCompletedWidget';
import { TodoFormWidget } from './TodoFormWidget';
import { TodoPendingWidget } from './TodoPendingWidget';
import { useTodoWidgets } from './useTodoWidgets';

export function TodosPage() {
  const controller = useTodoWidgets();

  return (
    <PageFrame>
      <Stack gap="md">
        <TodoFormWidget controller={controller} />
        <TodoPendingWidget controller={controller} />
        <TodoCompletedWidget controller={controller} />
      </Stack>
    </PageFrame>
  );
}
