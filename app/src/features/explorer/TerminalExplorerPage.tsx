import type { AgentSession } from "../terminal/agentSessions";
import { HubExplorerPage } from "./hub/HubExplorerPage";
import { WorktreeExplorerPage } from "./worktree/WorktreeExplorerPage";

type TerminalExplorerPageProps = {
  worktree: AgentSession | undefined;
};

export function TerminalExplorerPage({ worktree }: TerminalExplorerPageProps) {
  return worktree ? (
    <WorktreeExplorerPage
      project={worktree.project}
      taskId={worktree.task_id}
      workspacePath={worktree.workspace_path}
    />
  ) : (
    <HubExplorerPage />
  );
}
