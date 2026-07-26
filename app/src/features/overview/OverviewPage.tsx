import { useCallback, useState } from "react";

import { BacklogWidget } from "../backlog/BacklogWidget";
import { InboxWidget } from "../inbox/InboxWidget";
import { ProjectTabsWidget } from "../projects/ProjectTabsWidget";
import { useProjectSelection } from "../projects/useProjectSelection";
import { ResourceStatusWidget } from "../status/ResourceStatusWidget";
import { AllTasksWidget } from "../tasks/AllTasksWidget";
import type { SelectedTask } from "../tasks/AllTasksWidget";
import { TaskDependencyGraphWidget } from "../tasks/TaskDependencyGraphWidget";
import { TaskDetailWidget } from "../tasks/TaskDetailWidget";
import { TaskFlowGraphWidget } from "../tasks/TaskFlowGraphWidget";
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
  // 選択TaskはProjectタブと独立に保持し、タブ切替では解除しない
  const [selectedTask, setSelectedTask] = useState<SelectedTask | null>(null);
  const handleSelectTask = useCallback((project: string, taskId: string) => {
    setSelectedTask({ project, taskId });
  }, []);

  return (
    <OverviewFrame collapsed={collapsed}>
      <OverviewWide>
        <ProjectTabsWidget {...projectSelection} />
      </OverviewWide>
      <OverviewSide collapsed={collapsed.left} side="left">
        <TodoFormWidget controller={todoController} />
        <InboxWidget />
        <ResourceStatusWidget />
      </OverviewSide>
      <OverviewColumn>
        <TodoPendingWidget controller={todoController} showAllLink />
        <TaskDependencyGraphWidget
          height={480}
          onSelectTask={handleSelectTask}
          project={projectSelection.selectedProject}
        />
        <AllTasksWidget
          onSelectTask={handleSelectTask}
          selectedTask={selectedTask}
          showAllLink
        />
      </OverviewColumn>
      <OverviewSide collapsed={collapsed.right} side="right">
        {selectedTask && (
          <TaskFlowGraphWidget
            project={selectedTask.project}
            taskId={selectedTask.taskId}
          />
        )}
        <TaskDetailWidget
          emptyMessage="リストまたはグラフからTaskを選択してください"
          project={selectedTask?.project}
          taskId={selectedTask?.taskId}
        />
        <BacklogWidget project={projectSelection.selectedProject} />
      </OverviewSide>
    </OverviewFrame>
  );
}
