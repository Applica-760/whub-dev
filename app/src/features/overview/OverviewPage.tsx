import { InboxWidget } from '../inbox/InboxWidget';
import { ResourceStatusWidget } from '../status/ResourceStatusWidget';
import { TaskDependencyGraphWidget } from '../tasks/TaskDependencyGraphWidget';
import { TaskWidget } from '../tasks/TaskWidget';
import { TodoFormWidget } from '../todos/TodoFormWidget';
import { TodoPendingWidget } from '../todos/TodoPendingWidget';
import { useTodoWidgets } from '../todos/useTodoWidgets';
import { OverviewColumn, OverviewFrame } from './OverviewFrame';

export function OverviewPage() {
  const todoController = useTodoWidgets();

  return (
    <OverviewFrame>
      <OverviewColumn>
        <TodoFormWidget controller={todoController} />
        <InboxWidget />
        <ResourceStatusWidget />
      </OverviewColumn>
      <OverviewColumn>
        <TodoPendingWidget controller={todoController} showAllLink />
        <TaskWidget overviewOnly showAllLink />
      </OverviewColumn>
      <OverviewColumn>
        <TaskDependencyGraphWidget height={480} />
      </OverviewColumn>
    </OverviewFrame>
  );
}
