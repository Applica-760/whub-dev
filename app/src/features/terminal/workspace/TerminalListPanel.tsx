import { ActionIcon, Alert, Group, Text } from "@mantine/core";
import { IconPlus, IconRefresh } from "@tabler/icons-react";

import { GroupedListRow } from "../../../components/GroupedList";
import { TerminalWidgetFrame } from "../../../components/TerminalWidgetFrame";
import type { ApprovalAttention } from "../attentionApi";
import { targetHasAttention, type TerminalTarget } from "./terminalTarget";

type TerminalListPanelProps = {
  collapsed: boolean;
  error: string | null;
  loading: boolean;
  onReload: (value: string) => void;
  onSelect: (value: string) => void;
  onStartOperator: () => void;
  operatorPending: boolean;
  pendingAttention: ApprovalAttention[];
  selectedValue: string | null;
  targets: TerminalTarget[];
};

export function TerminalListPanel({
  collapsed,
  error,
  loading,
  onReload,
  onSelect,
  onStartOperator,
  operatorPending,
  pendingAttention,
  selectedValue,
  targets,
}: TerminalListPanelProps) {
  const hasWorktrees = targets.some((target) => target.kind === "worktree");
  return (
    <aside
      className="terminal-explorer"
      data-collapsed={collapsed || undefined}
    >
      <TerminalWidgetFrame>
        <Group className="terminal-list-header" justify="space-between">
          <Text fw={500} size="sm">
            Operations
          </Text>
          <ActionIcon
            aria-label="Operationを起動"
            disabled={operatorPending}
            onClick={onStartOperator}
            size="xs"
            title="Operationを起動"
            variant="subtle"
          >
            <IconPlus aria-hidden size={14} stroke={1.5} />
          </ActionIcon>
        </Group>
        {targets.map((target, index) => (
          <GroupedListRow
            key={target.value}
            onClick={() => onSelect(target.value)}
            rightSection={
              <Group gap={4} wrap="nowrap">
                {pendingAttention
                  .filter((item) => targetHasAttention(target, item))
                  .map((item) => {
                    const label =
                      item.event === "permission_request"
                        ? "権限リクエスト"
                        : "応答完了";
                    return (
                      <span
                        aria-label={label}
                        className="terminal-attention-dot"
                        data-event={item.event}
                        key={item.event}
                        role="img"
                        title={label}
                      />
                    );
                  })}
                <ActionIcon
                  aria-label={
                    target.kind === "operator"
                      ? `Operationを再読み込み: ${target.operatorId}`
                      : `Terminalを再読み込み: ${target.taskId} (${target.project})`
                  }
                  onClick={(event) => {
                    event.stopPropagation();
                    onReload(target.value);
                  }}
                  size="sm"
                  title="Terminalを再読み込み"
                  variant="subtle"
                >
                  <IconRefresh aria-hidden size={14} stroke={1.5} />
                </ActionIcon>
              </Group>
            }
            selected={selectedValue === target.value}
            subtitle={target.kind === "worktree" ? target.taskId : undefined}
            title={target.title}
            withDivider={index < targets.length - 1}
          />
        ))}
        {loading ? (
          <Text c="dimmed" p="md">
            Agent sessionを読み込んでいます…
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
