import { BacklogWidget } from '../backlog/BacklogWidget';
import { InboxWidget } from '../inbox/InboxWidget';
import { ProjectTabsWidget } from '../projects/ProjectTabsWidget';
import { useProjectSelection } from '../projects/useProjectSelection';
import { ResourceStatusWidget } from '../status/ResourceStatusWidget';
import { TaskDependencyGraphWidget } from '../tasks/TaskDependencyGraphWidget';
import { TaskWidget } from '../tasks/TaskWidget';
import { TodoFormWidget } from '../todos/TodoFormWidget';
import { TodoPendingWidget } from '../todos/TodoPendingWidget';
import { useTodoWidgets } from '../todos/useTodoWidgets';
import { OverviewColumn, OverviewFrame, OverviewWide } from './OverviewFrame';

export function OverviewPage() {
  const todoController = useTodoWidgets();
  const projectSelection = useProjectSelection();

  return (
    <OverviewFrame>
      <OverviewWide>
        <ProjectTabsWidget {...projectSelection} />
      </OverviewWide>
      <OverviewColumn>
        <TodoFormWidget controller={todoController} />
        <InboxWidget />
        <ResourceStatusWidget />
      </OverviewColumn>
      <OverviewColumn>
        <TodoPendingWidget controller={todoController} showAllLink />
        <TaskDependencyGraphWidget
          height={480}
          project={projectSelection.selectedProject}
        />
        <TaskWidget
          overviewOnly
          project={projectSelection.selectedProject}
          showAllLink
        />
      </OverviewColumn>
      <OverviewColumn>
        <BacklogWidget project={projectSelection.selectedProject} />
      </OverviewColumn>
    </OverviewFrame>
  );
}
