import { BacklogWidget } from "../backlog/BacklogWidget";
import { DailyWidgetFrame } from "../daily/DailyWidgetFrame";
import { ProjectTabsWidget } from "../projects/ProjectTabsWidget";
import { useProjectSelection } from "../projects/useProjectSelection";
import { ResourceStatusWidget } from "../status/ResourceStatusWidget";
import { TodoFormWidget } from "../todos/TodoFormWidget";
import { TodoPendingWidget } from "../todos/TodoPendingWidget";
import { useTodoWidgets } from "../todos/useTodoWidgets";
import {
  OverviewColumn,
  OverviewFrame,
  OverviewSide,
  OverviewWide,
} from "./OverviewFrame";
import type { OverviewCollapseState } from "./useOverviewCollapse";

type OverviewPageProps = {
  collapsed: OverviewCollapseState;
};

export function OverviewPage({ collapsed }: OverviewPageProps) {
  const todoController = useTodoWidgets();
  const projectSelection = useProjectSelection();
  return (
    <OverviewFrame collapsed={collapsed}>
      <OverviewWide>
        <ProjectTabsWidget {...projectSelection} />
      </OverviewWide>
      <OverviewSide collapsed={collapsed.left} side="left">
        <TodoFormWidget controller={todoController} />
        <DailyWidgetFrame />
        <ResourceStatusWidget />
      </OverviewSide>
      <OverviewColumn>
        <TodoPendingWidget controller={todoController} showAllLink />
        <BacklogWidget project={projectSelection.selectedProject} />
      </OverviewColumn>
    </OverviewFrame>
  );
}
