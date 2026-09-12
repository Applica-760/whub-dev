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
      issueNumber: number;
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
      title: `term${index + 1}`,
      value: `operator/${operator.operator_id}`,
    })),
    ...worktrees.map((worktree): TerminalTarget => ({
      kind: "worktree",
      project: worktree.project,
      issueNumber: worktree.issue_number,
      taskProject: worktree.project,
      title: worktree.project.slice(0, 4),
      value: `${worktree.project}/${worktree.issue_number}`,
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
        attention.issue_number === target.issueNumber;
}
