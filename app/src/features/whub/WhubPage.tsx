import { Stack} from '@mantine/core';

import { TodoPendingWidget } from '../todos/TodoPendingWidget';
import { useTodoWidgets } from '../todos/useTodoWidgets';

export function WhubPage() {
  const todoController = useTodoWidgets({ withForm: false });

  return (
    <div className="whub-overview">
      <div className="whub-overview-grid">
        <div className="whub-overview-todo">
          <Stack gap="md">
            <TodoPendingWidget controller={todoController} showAllLink />
          </Stack>
        </div>
      </div>
    </div>
  );
}
