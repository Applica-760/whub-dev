import { BacklogWidget } from "../backlog/BacklogWidget";
import { InboxWidget } from "../inbox/InboxWidget";
import { ProjectTabsWidget } from "../projects/ProjectTabsWidget";
import { useProjectSelection } from "../projects/useProjectSelection";
import { ResourceStatusWidget } from "../status/ResourceStatusWidget";
import { TaskDependencyGraphWidget } from "../tasks/TaskDependencyGraphWidget";
import { TaskWidget } from "../tasks/TaskWidget";
import { TodoFormWidget } from "../todos/TodoFormWidget";
import { TodoPendingWidget } from "../todos/TodoPendingWidget";
import { useTodoWidgets } from "../todos/useTodoWidgets";
import {
  OverviewColumn,
  OverviewFrame,
  OverviewSide,
  OverviewWide,
} from "./OverviewFrame";
import { useOverviewCollapse } from "./useOverviewCollapse";

export function OverviewPage() {
  const todoController = useTodoWidgets();
  const projectSelection = useProjectSelection();
  const { collapsed, toggle } = useOverviewCollapse();

  return (
    <OverviewFrame collapsed={collapsed}>
      <OverviewWide>
        <ProjectTabsWidget {...projectSelection} />
      </OverviewWide>
      <OverviewSide
        collapsed={collapsed.left}
        onToggle={() => toggle("left")}
        side="left"
      >
        <TodoFormWidget controller={todoController} />
        <InboxWidget />
        <ResourceStatusWidget />
      </OverviewSide>
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
      <OverviewSide
        collapsed={collapsed.right}
        onToggle={() => toggle("right")}
        side="right"
      >
        <BacklogWidget project={projectSelection.selectedProject} />
      </OverviewSide>
    </OverviewFrame>
  );
}
