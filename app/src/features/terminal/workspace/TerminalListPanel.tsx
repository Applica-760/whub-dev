import { ActionIcon, Alert, Badge, Button, Group, Text } from "@mantine/core";
import { IconRefresh, IconX } from "@tabler/icons-react";

import { GroupedListRow } from "../../../components/GroupedList";
import { TerminalWidgetFrame } from "../../../components/TerminalWidgetFrame";
import type { AgentSession } from "../agentSessions";
import type { ApprovalAttention } from "../attentionApi";
import type { OperatorTerminal } from "../operatorTerminals";
import { operatorValue, worktreeValue } from "./terminalValue";

type TerminalListPanelProps = {
  collapsed: boolean;
  error: string | null;
  loading: boolean;
  onReload: (value: string) => void;
  onSelect: (value: string) => void;
  onStartOperator: () => void;
  onStopOperator: (operatorId: string) => void;
  operatorPending: boolean;
  operators: OperatorTerminal[];
  pendingAttention: ApprovalAttention[];
  selectedTerminal: string | null;
  terminals: AgentSession[];
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
  operators,
  pendingAttention,
  selectedTerminal,
  terminals,
}: TerminalListPanelProps) {
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
        {operators.map((operator, index) => {
          const value = operatorValue(operator.operator_id);
          return (
            <GroupedListRow
              key={operator.operator_id}
              onClick={() => onSelect(value)}
              rightSection={
                <Group gap={4} wrap="nowrap">
                  {pendingAttention
                    .filter(
                      (item) =>
                        item.target === "operator" &&
                        item.operator_id === operator.operator_id,
                    )
                    .map((item) => (
                      <Badge
                        color={
                          item.event === "permission_request"
                            ? "yellow"
                            : "blue"
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
                      aria-label={`Operationを再読み込み: ${operator.operator_id}`}
                      onClick={(event) => {
                        event.stopPropagation();
                        onReload(value);
                      }}
                      title="Terminalを再読み込み"
                      variant="subtle"
                    >
                      <IconRefresh aria-hidden size={16} stroke={1.5} />
                    </ActionIcon>
                    <ActionIcon
                      aria-label={`Operation ${operator.operator_id}を停止`}
                      disabled={operatorPending}
                      onClick={(event) => {
                        event.stopPropagation();
                        onStopOperator(operator.operator_id);
                      }}
                      title="Operationを終了"
                      variant="subtle"
                    >
                      <IconX aria-hidden size={16} stroke={1.5} />
                    </ActionIcon>
                  </Group>
                </Group>
              }
              selected={selectedTerminal === value}
              title={`Operation ${index + 1}`}
              withDivider={operators.length > 1 || terminals.length > 0}
            />
          );
        })}
        {terminals.map((worktree, index) => {
          const value = worktreeValue(worktree);
          return (
            <GroupedListRow
              key={value}
              onClick={() => onSelect(value)}
              rightSection={
                <Group gap={4} wrap="nowrap">
                  {pendingAttention
                    .filter(
                      (item) =>
                        item.target === "worktree" &&
                        item.project === worktree.project &&
                        item.task_id === worktree.task_id,
                    )
                    .map((item) => (
                      <Badge
                        color={
                          item.event === "permission_request"
                            ? "yellow"
                            : "blue"
                        }
                        key={item.event}
                        size="sm"
                      >
                        {item.event === "permission_request"
                          ? "承認待ち"
                          : "応答終了"}
                      </Badge>
                    ))}
                  <ActionIcon
                    aria-label={`Terminalを再読み込み: ${worktree.task_id} (${worktree.project})`}
                    onClick={(event) => {
                      event.stopPropagation();
                      onReload(value);
                    }}
                    title="Terminalを再読み込み"
                    variant="subtle"
                  >
                    <IconRefresh aria-hidden size={16} stroke={1.5} />
                  </ActionIcon>
                </Group>
              }
              selected={value === selectedTerminal}
              subtitle={worktree.task_id}
              title={worktree.project}
              withDivider={index < terminals.length - 1}
            />
          );
        })}
        {loading ? (
          <Text c="dimmed" p="md">
            Agent sessionを読み込んでいます…
          </Text>
        ) : terminals.length === 0 ? (
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
