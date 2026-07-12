import { TodoPendingWidget } from '../todos/TodoPendingWidget';
import { useTodoWidgets } from '../todos/useTodoWidgets';
import { OverviewColumn, OverviewFrame } from './OverviewFrame';

export function OverviewPage() {
  const todoController = useTodoWidgets({ withForm: false });

  return (
    <OverviewFrame>
      <OverviewColumn>
        <TodoPendingWidget controller={todoController} showAllLink />
        <TodoPendingWidget controller={todoController} showAllLink />
      </OverviewColumn>
      <OverviewColumn>
        <TodoPendingWidget controller={todoController} showAllLink />
      </OverviewColumn>
      <OverviewColumn>
        <TodoPendingWidget controller={todoController} showAllLink />
      </OverviewColumn>
    </OverviewFrame>
  );
}
