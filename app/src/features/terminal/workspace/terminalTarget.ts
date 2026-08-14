import type { AgentSession } from "../agentSessions";
import type { ApprovalAttention } from "../attentionApi";
import type { OperatorTerminal } from "../operatorTerminals";

export type TerminalTarget =
  | {
      kind: "operator";
      operatorId: string;
      taskProject: "whub-dev";
      title: string;
      value: string;
    }
  | {
      kind: "worktree";
      project: string;
      taskId: string;
      taskProject: string;
      title: string;
      value: string;
    };

export function terminalTargets(
  operators: OperatorTerminal[],
  worktrees: AgentSession[],
): TerminalTarget[] {
  return [
    ...operators.map((operator, index): TerminalTarget => ({
      kind: "operator",
      operatorId: operator.operator_id,
      taskProject: "whub-dev",
      title: `Operation ${index + 1}`,
      value: `operator/${operator.operator_id}`,
    })),
    ...worktrees.map((worktree): TerminalTarget => ({
      kind: "worktree",
      project: worktree.project,
      taskId: worktree.task_id,
      taskProject: worktree.project,
      title: worktree.project,
      value: `${worktree.project}/${worktree.task_id}`,
    })),
  ];
}

export function targetHasAttention(
  target: TerminalTarget,
  attention: ApprovalAttention,
) {
  return target.kind === "operator"
    ? attention.target === "operator" &&
        attention.operator_id === target.operatorId
    : attention.target === "worktree" &&
        attention.project === target.project &&
        attention.task_id === target.taskId;
}
