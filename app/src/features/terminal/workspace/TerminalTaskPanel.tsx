import { TaskDependencyGraphWidget } from "../../tasks/TaskDependencyGraphWidget";
import { TaskDetailWidget } from "../../tasks/TaskDetailWidget";

type TerminalTaskPanelProps = {
  collapsed: boolean;
  detailProject?: string;
  detailTaskId?: string;
  emptyMessage: string;
  graphProject: string | null;
  onSelectTask: (project: string, taskId: string) => void;
};

export function TerminalTaskPanel({
  collapsed,
  detailProject,
  detailTaskId,
  emptyMessage,
  graphProject,
  onSelectTask,
}: TerminalTaskPanelProps) {
  return (
    <aside
      className="terminal-task-panel"
      data-collapsed={collapsed || undefined}
    >
      <div className="terminal-task-graph">
        <TaskDependencyGraphWidget
          active
          height="100%"
          hideTitle
          onSelectTask={onSelectTask}
          project={graphProject}
        />
      </div>
      <div className="terminal-task-detail">
        <TaskDetailWidget
          active
          emptyMessage={emptyMessage}
          hideTitle
          project={detailProject}
          taskId={detailTaskId}
        />
      </div>
    </aside>
  );
}
