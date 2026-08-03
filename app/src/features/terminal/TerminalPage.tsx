import { Alert, Badge, Button, Group, Switch, Text } from "@mantine/core";
import { useCallback, useEffect, useMemo, useState } from "react";

import { requestJson } from "../../api/client";
import { GroupedListRow } from "../../components/GroupedList";
import { WidgetFrame } from "../../components/WidgetFrame";
import type { WorktreeItem } from "../worktrees/api";
import { useWorktrees } from "../worktrees/useWorktrees";
import { DiffPane } from "./DiffPane";
import { CodexPanel } from "./CodexPanel";
import { TerminalWidget } from "./TerminalWidget";
import { useApprovalAttention } from "./useApprovalAttention";

import "./terminal.css";

type TerminalWorktree = WorktreeItem & {
  parent_project: string;
  task_id: string;
};
type OperatorTerminal = { operator_id: string | null; state: "off" | "on" };
type PanelMode = "terminal" | "agent";

function terminalWorktrees(worktrees: WorktreeItem[]): TerminalWorktree[] {
  return worktrees.filter(
    (worktree): worktree is TerminalWorktree =>
      worktree.parent_project !== null && worktree.task_id !== null,
  );
}

function worktreeValue(worktree: WorktreeItem) {
  return `${worktree.parent_project}/${worktree.task_id}`;
}

export function TerminalPage() {
  const { error, loading, worktrees } = useWorktrees();
  const { acknowledge, attention } = useApprovalAttention();
  const terminals = useMemo(() => terminalWorktrees(worktrees), [worktrees]);
  const [selectedTerminal, setSelectedTerminal] = useState<string | null>(null);
  const [operator, setOperator] = useState<OperatorTerminal | null>(null);
  const [operatorError, setOperatorError] = useState<string | null>(null);
  const [operatorPending, setOperatorPending] = useState(false);
  const [panelMode, setPanelMode] = useState<PanelMode>("terminal");
  const selectedWorktree = terminals.find(
    (item) => worktreeValue(item) === selectedTerminal,
  );
  const pendingAttention = attention.filter((item) => !item.acknowledged);
  const operatorRunning =
    operator?.state === "on" && operator.operator_id !== null;

  const acknowledgeTerminal = useCallback(
    (value: string) => {
      const worktree = terminals.find((item) => worktreeValue(item) === value);
      if (!worktree) return;
      const item = pendingAttention.find(
        (attentionItem) =>
          attentionItem.project === worktree.parent_project &&
          attentionItem.task_id === worktree.task_id,
      );
      if (item) void acknowledge(item.project, item.task_id);
    },
    [acknowledge, pendingAttention, terminals],
  );

  const openTerminal = useCallback(
    (value: string) => {
      setSelectedTerminal(value);
      setPanelMode("terminal");
      acknowledgeTerminal(value);
    },
    [acknowledgeTerminal],
  );

  useEffect(() => {
    setSelectedTerminal((current) => {
      if (current === "operator" && operatorRunning) return current;
      return terminals.some((item) => worktreeValue(item) === current)
        ? current
        : terminals[0]
          ? worktreeValue(terminals[0])
          : null;
    });
  }, [operatorRunning, terminals]);

  useEffect(() => {
    if (!selectedWorktree) setPanelMode("terminal");
  }, [selectedWorktree]);

  const refreshOperator = useCallback(async () => {
    try {
      setOperator(
        await requestJson<OperatorTerminal>("/api/operator-terminal"),
      );
    } catch (requestError) {
      setOperatorError(
        requestError instanceof Error
          ? requestError.message
          : "Operator Terminalを読み込めませんでした。",
      );
    }
  }, []);

  useEffect(() => {
    void refreshOperator();
  }, [refreshOperator]);

  const toggleOperator = useCallback(async () => {
    if (operatorRunning && !window.confirm("Operator Terminalを停止しますか？"))
      return;
    setOperatorPending(true);
    setOperatorError(null);
    try {
      const updated = await requestJson<OperatorTerminal>(
        "/api/operator-terminal",
        {
          method: operatorRunning ? "DELETE" : "POST",
        },
      );
      setOperator(updated);
      setSelectedTerminal(
        updated.state === "on"
          ? "operator"
          : terminals[0]
            ? worktreeValue(terminals[0])
            : null,
      );
    } catch (requestError) {
      setOperatorError(
        requestError instanceof Error
          ? requestError.message
          : "Operator Terminalを更新できませんでした。",
      );
    } finally {
      setOperatorPending(false);
    }
  }, [operatorRunning, terminals]);

  return (
    <main className="terminal-page">
      {pendingAttention.length > 0 && (
        <Alert
          color="yellow"
          title="承認待ちのTerminalがあります"
          variant="light"
        >
          <Group justify="space-between">
            <Text size="sm">
              {pendingAttention[0].project} / {pendingAttention[0].task_id}
            </Text>
            <Button
              onClick={() => {
                openTerminal(
                  `${pendingAttention[0].project}/${pendingAttention[0].task_id}`,
                );
              }}
              size="xs"
              variant="light"
            >
              Terminalを開く
            </Button>
          </Group>
        </Alert>
      )}
      <section className="terminal-layout">
        <WidgetFrame title={<Text fw={600}>Explorer</Text>}>
          <Group justify="space-between" m="md">
            <Text fw={500}>Operator</Text>
            <Switch
              aria-label={operatorRunning ? "Operatorを停止" : "Operatorを開始"}
              checked={operatorRunning}
              disabled={operatorPending}
              offLabel="OFF"
              onChange={() => void toggleOperator()}
              onLabel="ON"
              size="md"
            />
          </Group>
          {operatorRunning && (
            <GroupedListRow
              onClick={() => setSelectedTerminal("operator")}
              selected={selectedTerminal === "operator"}
              subtitle="workspace-hub"
              title="Operator Terminal"
              withDivider={terminals.length > 0}
            />
          )}
          {loading ? (
            <Text c="dimmed" p="md">
              worktreeを読み込んでいます…
            </Text>
          ) : terminals.length === 0 ? (
            <Text c="dimmed" p="md">
              worktreeがありません
            </Text>
          ) : (
            terminals.map((worktree, index) => (
              <GroupedListRow
                key={worktreeValue(worktree)}
                onClick={() => openTerminal(worktreeValue(worktree))}
                rightSection={
                  pendingAttention.some(
                    (item) =>
                      item.project === worktree.parent_project &&
                      item.task_id === worktree.task_id,
                  ) ? (
                    <Badge color="yellow" size="sm">
                      承認待ち
                    </Badge>
                  ) : undefined
                }
                selected={worktreeValue(worktree) === selectedTerminal}
                subtitle={worktree.task_id}
                title={worktree.parent_project}
                withDivider={index < terminals.length - 1}
              />
            ))
          )}
          {(error || operatorError) && (
            <Alert color="red" m="md">
              {error ?? operatorError}
            </Alert>
          )}
        </WidgetFrame>
        <WidgetFrame
          action={
            <Group gap={4}>
              <Button
                aria-pressed={panelMode === "terminal"}
                onClick={() => {
                  setPanelMode("terminal");
                  if (selectedWorktree)
                    acknowledgeTerminal(worktreeValue(selectedWorktree));
                }}
                size="compact-xs"
                variant={panelMode === "terminal" ? "light" : "subtle"}
              >
                Terminal
              </Button>
              <Button
                aria-pressed={panelMode === "agent"}
                disabled={!selectedWorktree}
                onClick={() => setPanelMode("agent")}
                size="compact-xs"
                variant={panelMode === "agent" ? "light" : "subtle"}
              >
                Agent
              </Button>
            </Group>
          }
          title={
            <Text fw={600}>
              {panelMode === "terminal" ? "Terminal" : "Agent"}
            </Text>
          }
        >
          {panelMode === "agent" && selectedWorktree ? (
            <CodexPanel
              project={selectedWorktree.parent_project}
              taskId={selectedWorktree.task_id}
            />
          ) : operatorRunning && selectedTerminal === "operator" ? (
            <TerminalWidget
              endpoint={`/api/operator-terminals/${encodeURIComponent(operator?.operator_id ?? "")}`}
              label="Operator / workspace-hub"
              resizeSignal={selectedTerminal}
            />
          ) : selectedWorktree ? (
            <TerminalWidget
              project={selectedWorktree.parent_project}
              resizeSignal={selectedTerminal ?? ""}
              taskId={selectedWorktree.task_id}
            />
          ) : (
            <Text c="dimmed" p="md">
              表示できる端末はありません。
            </Text>
          )}
        </WidgetFrame>
      </section>
      <DiffPane
        project={selectedWorktree?.parent_project}
        taskId={selectedWorktree?.task_id}
      />
    </main>
  );
}
