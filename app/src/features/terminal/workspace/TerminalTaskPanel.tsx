import type { SelectedTask } from "../../tasks/AllTasksWidget";
import { TaskDependencyGraphWidget } from "../../tasks/TaskDependencyGraphWidget";
import { TaskDetailWidget } from "../../tasks/TaskDetailWidget";
import type { AgentSession } from "../agentSessions";

type TerminalTaskPanelProps = {
  collapsed: boolean;
  onSelectTask: (project: string, taskId: string) => void;
  operatorSelected: boolean;
  selectedTask: SelectedTask | null;
  selectedWorktree?: AgentSession;
};

export function TerminalTaskPanel({
  collapsed,
  onSelectTask,
  operatorSelected,
  selectedTask,
  selectedWorktree,
}: TerminalTaskPanelProps) {
  const graphProject = operatorSelected
    ? "whub-dev"
    : (selectedWorktree?.project ?? null);
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
          emptyMessage={
            operatorSelected
              ? "グラフからTaskを選択してください"
              : "Terminalを選択してください"
          }
          hideTitle
          project={selectedTask?.project ?? selectedWorktree?.project}
          taskId={selectedTask?.taskId ?? selectedWorktree?.task_id}
        />
      </div>
    </aside>
  );
}
