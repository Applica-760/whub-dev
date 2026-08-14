import { ActionIcon, Alert, Badge, Button, Group, Text } from "@mantine/core";
import { IconRefresh, IconX } from "@tabler/icons-react";

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
  onStopOperator: (operatorId: string) => void;
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
  onStopOperator,
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
        <Group justify="space-between" m="md">
          <Text fw={500}>Operations</Text>
          <Button
            aria-label="Operationを起動"
            disabled={operatorPending}
            onClick={onStartOperator}
            size="xs"
          >
            起動
          </Button>
        </Group>
        {targets.map((target, index) => (
          <GroupedListRow
            key={target.value}
            onClick={() => onSelect(target.value)}
            rightSection={
              <Group gap={4} wrap="nowrap">
                {pendingAttention
                  .filter((item) => targetHasAttention(target, item))
                  .map((item) => (
                    <Badge
                      color={
                        item.event === "permission_request" ? "yellow" : "blue"
                      }
                      key={item.event}
                      size="sm"
                    >
                      {item.event === "permission_request"
                        ? "承認待ち"
                        : "応答終了"}
                    </Badge>
                  ))}
                <Group gap={0} wrap="nowrap">
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
                    title="Terminalを再読み込み"
                    variant="subtle"
                  >
                    <IconRefresh aria-hidden size={16} stroke={1.5} />
                  </ActionIcon>
                  {target.kind === "operator" && (
                    <ActionIcon
                      aria-label={`Operation ${target.operatorId}を停止`}
                      disabled={operatorPending}
                      onClick={(event) => {
                        event.stopPropagation();
                        onStopOperator(target.operatorId);
                      }}
                      title="Operationを終了"
                      variant="subtle"
                    >
                      <IconX aria-hidden size={16} stroke={1.5} />
                    </ActionIcon>
                  )}
                </Group>
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
