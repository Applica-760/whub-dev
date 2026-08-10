import { Alert, Badge, Button, Group, Switch, Text } from "@mantine/core";
import { useCallback, useEffect, useMemo, useState } from "react";

import { requestJson } from "../../api/client";
import { GroupedListRow } from "../../components/GroupedList";
import { WidgetFrame } from "../../components/WidgetFrame";
import type { WorktreeItem } from "../worktrees/api";
import { useWorktrees } from "../worktrees/useWorktrees";
import { DiffPane } from "./DiffPane";
import { TerminalWidget } from "./TerminalWidget";
import { useApprovalAttention } from "./useApprovalAttention";
import type { TerminalCollapseState } from "./useTerminalCollapse";
import type { SelectedTask } from "../tasks/AllTasksWidget";
import { TaskDependencyGraphWidget } from "../tasks/TaskDependencyGraphWidget";
import { TaskDetailWidget } from "../tasks/TaskDetailWidget";

import "./terminal.css";

type TerminalWorktree = WorktreeItem & {
  parent_project: string;
  task_id: string;
};
type OperatorTerminal = { operator_id: string };
type OperatorTerminals = { terminals: OperatorTerminal[] };

function terminalWorktrees(worktrees: WorktreeItem[]): TerminalWorktree[] {
  return worktrees.filter(
    (worktree): worktree is TerminalWorktree =>
      worktree.parent_project !== null && worktree.task_id !== null,
  );
}

function worktreeValue(worktree: WorktreeItem) {
  return `${worktree.parent_project}/${worktree.task_id}`;
}

function operatorValue(operatorId: string) {
  return `operator/${operatorId}`;
}

type TerminalPageProps = {
  collapsed?: TerminalCollapseState;
};

export function TerminalPage({
  collapsed = { left: false, right: false },
}: TerminalPageProps) {
  const { error, loading, worktrees } = useWorktrees();
  const { acknowledgeOperator, acknowledgeWorktree, attention } =
    useApprovalAttention();
  const terminals = useMemo(() => terminalWorktrees(worktrees), [worktrees]);
  const [selectedTerminal, setSelectedTerminal] = useState<string | null>(null);
  const [operators, setOperators] = useState<OperatorTerminal[]>([]);
  const [operatorError, setOperatorError] = useState<string | null>(null);
  const [operatorsLoaded, setOperatorsLoaded] = useState(false);
  const [operatorPending, setOperatorPending] = useState(false);
  const [selectedOperationTask, setSelectedOperationTask] =
    useState<SelectedTask | null>(null);
  const selectedWorktree = terminals.find(
    (item) => worktreeValue(item) === selectedTerminal,
  );
  const pendingAttention = attention.filter((item) => !item.acknowledged);
  const selectedOperator = operators.find(
    (operator) => operatorValue(operator.operator_id) === selectedTerminal,
  );
  const graphProject = selectedOperator
    ? "whub-dev"
    : (selectedWorktree?.parent_project ?? null);
  const detailProject = selectedOperator
    ? selectedOperationTask?.project
    : selectedWorktree?.parent_project;
  const detailTaskId = selectedOperator
    ? selectedOperationTask?.taskId
    : selectedWorktree?.task_id;

  const acknowledgeTerminal = useCallback(
    (value: string) => {
      const worktree = terminals.find((item) => worktreeValue(item) === value);
      if (!worktree) return;
      const item = pendingAttention.find(
        (attentionItem) =>
          attentionItem.target === "worktree" &&
          attentionItem.project === worktree.parent_project &&
          attentionItem.task_id === worktree.task_id,
      );
      if (item)
        void acknowledgeWorktree(worktree.parent_project, worktree.task_id);
    },
    [acknowledgeWorktree, pendingAttention, terminals],
  );

  const openOperator = useCallback(
    (operatorId: string) => {
      setSelectedTerminal(operatorValue(operatorId));
      if (
        pendingAttention.some(
          (item) =>
            item.target === "operator" && item.operator_id === operatorId,
        )
      )
        void acknowledgeOperator(operatorId);
    },
    [acknowledgeOperator, pendingAttention],
  );

  const openTerminal = useCallback(
    (value: string) => {
      setSelectedTerminal(value);
      acknowledgeTerminal(value);
    },
    [acknowledgeTerminal],
  );

  const terminalValues = useMemo(
    () => [
      ...operators.map((operator) => operatorValue(operator.operator_id)),
      ...terminals.map(worktreeValue),
    ],
    [operators, terminals],
  );

  const selectTerminal = useCallback(
    (value: string) => {
      const operator = operators.find(
        (item) => operatorValue(item.operator_id) === value,
      );
      if (operator) openOperator(operator.operator_id);
      else openTerminal(value);
    },
    [openOperator, openTerminal, operators],
  );

  const selectOperationTask = useCallback((project: string, taskId: string) => {
    setSelectedOperationTask({ project, taskId });
  }, []);

  useEffect(() => {
    setSelectedTerminal((current) => {
      if (!operatorsLoaded) return current;
      if (
        operators.some(
          (operator) => operatorValue(operator.operator_id) === current,
        )
      )
        return current;
      if (operators[0]) return operatorValue(operators[0].operator_id);
      if (loading) return current;
      return terminals.some((item) => worktreeValue(item) === current)
        ? current
        : terminals[0]
          ? worktreeValue(terminals[0])
          : null;
    });
  }, [loading, operators, operatorsLoaded, terminals]);

  useEffect(() => {
    const acknowledgeSelected = () => {
      if (selectedOperator)
        void acknowledgeOperator(selectedOperator.operator_id);
      else if (selectedWorktree)
        void acknowledgeWorktree(
          selectedWorktree.parent_project,
          selectedWorktree.task_id,
        );
    };
    const onVisibilityChange = () => {
      if (document.visibilityState === "visible") acknowledgeSelected();
    };
    document.addEventListener("visibilitychange", onVisibilityChange);
    return () =>
      document.removeEventListener("visibilitychange", onVisibilityChange);
  }, [
    acknowledgeOperator,
    acknowledgeWorktree,
    selectedOperator,
    selectedWorktree,
  ]);

  const refreshOperator = useCallback(async () => {
    try {
      const listed = await requestJson<OperatorTerminals>(
        "/api/operator-terminals",
      );
      setOperators((current) =>
        current.length === listed.terminals.length &&
        current.every(
          (operator, index) =>
            operator.operator_id === listed.terminals[index]?.operator_id,
        )
          ? current
          : listed.terminals,
      );
    } catch (requestError) {
      setOperatorError(
        requestError instanceof Error
          ? requestError.message
          : "Operator Terminalを読み込めませんでした。",
      );
    } finally {
      setOperatorsLoaded(true);
    }
  }, []);

  useEffect(() => {
    void refreshOperator();
  }, [refreshOperator]);

  const startOperator = useCallback(async () => {
    setOperatorPending(true);
    setOperatorError(null);
    try {
      const created = await requestJson<OperatorTerminal>(
        "/api/operator-terminals",
        { method: "POST" },
      );
      setOperators((current) => [...current, created]);
      openOperator(created.operator_id);
    } catch (requestError) {
      setOperatorError(
        requestError instanceof Error
          ? requestError.message
          : "Operator Terminalを更新できませんでした。",
      );
    } finally {
      setOperatorPending(false);
    }
  }, [openOperator]);

  const stopOperator = useCallback(async (operatorId: string) => {
    if (!window.confirm("Operationを終了しますか？")) return;
    setOperatorPending(true);
    setOperatorError(null);
    try {
      await requestJson<void>(
        `/api/operator-terminals/${encodeURIComponent(operatorId)}`,
        { method: "DELETE" },
      );
      setOperators((current) =>
        current.filter((item) => item.operator_id !== operatorId),
      );
    } catch (requestError) {
      setOperatorError(
        requestError instanceof Error
          ? requestError.message
          : "Operationを終了できませんでした。",
      );
    } finally {
      setOperatorPending(false);
    }
  }, []);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (
        !event.metaKey ||
        !event.shiftKey ||
        event.altKey ||
        event.ctrlKey ||
        !(event.target instanceof Element) ||
        !event.target.closest(".xterm-view")
      )
        return;

      if (event.code === "KeyO") {
        if (!operatorPending) {
          event.preventDefault();
          void startOperator();
        }
        return;
      }
      if (
        !terminalValues.length ||
        (event.key !== "ArrowUp" && event.key !== "ArrowDown")
      )
        return;

      event.preventDefault();
      const index = terminalValues.indexOf(selectedTerminal ?? "");
      const nextIndex =
        event.key === "ArrowDown"
          ? (index + 1 + terminalValues.length) % terminalValues.length
          : index <= 0
            ? terminalValues.length - 1
            : index - 1;
      selectTerminal(terminalValues[nextIndex]);
    };
    window.addEventListener("keydown", onKeyDown, true);
    return () => window.removeEventListener("keydown", onKeyDown, true);
  }, [
    operatorPending,
    selectedTerminal,
    selectTerminal,
    startOperator,
    terminalValues,
  ]);

  return (
    <main className="terminal-page">
      <section
        className="terminal-layout"
        data-explorer-collapsed={collapsed.left || undefined}
        data-task-collapsed={collapsed.right || undefined}
      >
        <aside
          className="terminal-task-panel"
          data-collapsed={collapsed.right || undefined}
        >
          <div className="terminal-task-graph">
            <TaskDependencyGraphWidget
              height="100%"
              onSelectTask={selectedOperator ? selectOperationTask : undefined}
              project={graphProject}
            />
          </div>
          <div className="terminal-task-detail">
            <TaskDetailWidget
              emptyMessage={
                selectedOperator
                  ? "グラフからTaskを選択してください"
                  : "Terminalを選択してください"
              }
              project={detailProject}
              taskId={detailTaskId}
            />
          </div>
        </aside>
        <WidgetFrame title={<Text fw={600}>Terminal</Text>}>
          {selectedOperator ? (
            <TerminalWidget
              endpoint={`/api/operator-terminals/${encodeURIComponent(selectedOperator.operator_id)}`}
              key={selectedTerminal}
              label="Operation / workspace-hub"
              resizeSignal={`${selectedTerminal ?? ""}:${collapsed.left}:${collapsed.right}`}
            />
          ) : selectedWorktree ? (
            <TerminalWidget
              key={selectedTerminal}
              project={selectedWorktree.parent_project}
              resizeSignal={`${selectedTerminal ?? ""}:${collapsed.left}:${collapsed.right}`}
              taskId={selectedWorktree.task_id}
            />
          ) : (
            <Text c="dimmed" p="md">
              表示できる端末はありません。
            </Text>
          )}
        </WidgetFrame>
        <aside
          className="terminal-explorer"
          data-collapsed={collapsed.left || undefined}
        >
          <WidgetFrame title={<Text fw={600}>Explorer</Text>}>
            <Group justify="space-between" m="md">
              <Text fw={500}>Operations</Text>
              <Button
                aria-label="Operationを起動"
                disabled={operatorPending}
                onClick={() => void startOperator()}
                size="xs"
              >
                起動
              </Button>
            </Group>
            {operators.map((operator, index) => (
              <GroupedListRow
                key={operator.operator_id}
                onClick={() => openOperator(operator.operator_id)}
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
                    <Switch
                      aria-label={`Operation ${operator.operator_id}を停止`}
                      checked
                      color="green"
                      disabled={operatorPending}
                      onClick={(event) => {
                        event.stopPropagation();
                      }}
                      onChange={() => void stopOperator(operator.operator_id)}
                      offLabel="OFF"
                      onLabel="ON"
                      size="md"
                    />
                  </Group>
                }
                selected={
                  selectedTerminal === operatorValue(operator.operator_id)
                }
                subtitle="workspace-hub"
                title={`Operation ${index + 1}`}
                withDivider={operators.length > 1 || terminals.length > 0}
              />
            ))}
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
                        item.target === "worktree" &&
                        item.project === worktree.parent_project &&
                        item.task_id === worktree.task_id,
                    ) ? (
                      <Group gap={4} wrap="nowrap">
                        {pendingAttention
                          .filter(
                            (item) =>
                              item.target === "worktree" &&
                              item.project === worktree.parent_project &&
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
                      </Group>
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
        </aside>
      </section>
      <DiffPane
        project={selectedWorktree?.parent_project}
        taskId={selectedWorktree?.task_id}
        workspacePath={selectedWorktree?.workspace_path}
      />
    </main>
  );
}
