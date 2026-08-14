import type { AgentSession } from "../agentSessions";

export function worktreeValue(worktree: AgentSession) {
  return `${worktree.project}/${worktree.task_id}`;
}

export function operatorValue(operatorId: string) {
  return `operator/${operatorId}`;
}
