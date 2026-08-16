import { Alert, Text } from "@mantine/core";

import { GroupedListRow } from "../../../components/GroupedList";
import { TerminalWidgetFrame } from "../../../components/TerminalWidgetFrame";
import type { ApprovalAttention } from "../attentionApi";
import { targetHasAttention, type TerminalTarget } from "./terminalTarget";

type TerminalListPanelProps = {
  collapsed: boolean;
  error: string | null;
  loading: boolean;
  onSelect: (value: string) => void;
  pendingAttention: ApprovalAttention[];
  selectedValue: string | null;
  targets: TerminalTarget[];
};

export function TerminalListPanel({
  collapsed,
  error,
  loading,
  onSelect,
  pendingAttention,
  selectedValue,
  targets,
}: TerminalListPanelProps) {
  const hasWorktrees = targets.some((target) => target.kind === "worktree");
  const attentionSlots = [
    ["permission_request", "権限待ち"],
    ["response_completed", "完了"],
  ] as const;
  return (
    <aside
      className="terminal-explorer"
      data-collapsed={collapsed || undefined}
    >
      <TerminalWidgetFrame>
        {targets.map((target, index) => {
          const targetAttention = pendingAttention.filter((item) =>
            targetHasAttention(target, item),
          );
          return (
            <GroupedListRow
              key={target.value}
              onClick={() => onSelect(target.value)}
              rightSection={
                <span className="terminal-attention-slots">
                  {attentionSlots.map(([event, label]) => {
                    const active = targetAttention.some(
                      (item) => item.event === event,
                    );
                    return (
                      <span
                        aria-hidden={!active}
                        aria-label={active ? label : undefined}
                        className="terminal-attention-dot"
                        data-active={active || undefined}
                        data-event={event}
                        key={event}
                        role={active ? "img" : undefined}
                        title={active ? label : undefined}
                      />
                    );
                  })}
                </span>
              }
              selected={selectedValue === target.value}
              subtitle={
                target.kind === "worktree"
                  ? (target.taskId.match(/\d+$/)?.[0] ?? target.taskId)
                  : undefined
              }
              title={target.title}
              withDivider={index < targets.length - 1}
            />
          );
        })}
        {loading ? (
          <Text c="dimmed" p="md">
            読込中…
          </Text>
        ) : !hasWorktrees ? (
          <Text c="dimmed" p="md">
            Agent sessionがありません
          </Text>
        ) : null}
        {error && (
          <Alert color="red" m="md">
            {error}
          </Alert>
        )}
      </TerminalWidgetFrame>
    </aside>
  );
}
