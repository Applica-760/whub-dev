import { Alert, Badge, Button, Group, Text } from "@mantine/core";
import { useCallback, useEffect, useMemo, useState } from "react";

import { GroupedListRow } from "../../components/GroupedList";
import { WidgetFrame } from "../../components/WidgetFrame";
import {
  OverviewColumn,
  OverviewFrame,
  OverviewSide,
} from "../overview/OverviewFrame";
import type { OverviewCollapseState } from "../overview/useOverviewCollapse";
import type { WorktreeItem } from "../worktrees/api";
import { useWorktrees } from "../worktrees/useWorktrees";
import { TerminalWidget } from "./TerminalWidget";
import { requestJson } from "../../api/client";

import "./terminal.css";

type TerminalWorktree = WorktreeItem & {
  parent_project: string;
  task_id: string;
};

type TerminalPageProps = {
  collapsed: OverviewCollapseState;
};

type OperatorTerminal = {
  operator_id: string | null;
  state: "off" | "on";
};

function terminalWorktrees(worktrees: WorktreeItem[]): TerminalWorktree[] {
  return worktrees.filter(
    (worktree): worktree is TerminalWorktree =>
      worktree.parent_project !== null && worktree.task_id !== null,
  );
}

function worktreeValue(worktree: WorktreeItem) {
  return `${worktree.parent_project}/${worktree.task_id}`;
}

export function TerminalPage({ collapsed }: TerminalPageProps) {
  const { error, loading, worktrees } = useWorktrees();
  const terminals = useMemo(() => terminalWorktrees(worktrees), [worktrees]);
  const [selectedTerminal, setSelectedTerminal] = useState<string | null>(null);
  const [operator, setOperator] = useState<OperatorTerminal | null>(null);
  const [operatorError, setOperatorError] = useState<string | null>(null);
  const [operatorPending, setOperatorPending] = useState(false);
  const selectedWorktree = terminals.find(
    (worktree) => worktreeValue(worktree) === selectedTerminal,
  );

  useEffect(() => {
    setSelectedTerminal((current) => {
      if (current === "operator" && operator?.state === "on") {
        return current;
      }
      if (
        current &&
        terminals.some((worktree) => worktreeValue(worktree) === current)
      ) {
        return current;
      }
      return terminals[0] ? worktreeValue(terminals[0]) : null;
    });
  }, [operator?.state, terminals]);

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

  const startOperator = useCallback(async () => {
    setOperatorPending(true);
    setOperatorError(null);
    try {
      const started = await requestJson<OperatorTerminal>(
        "/api/operator-terminal",
        {
          method: "POST",
        },
      );
      setOperator(started);
      setSelectedTerminal("operator");
    } catch (requestError) {
      setOperatorError(
        requestError instanceof Error
          ? requestError.message
          : "Operator Terminalを開始できませんでした。",
      );
    } finally {
      setOperatorPending(false);
    }
  }, []);

  const stopOperator = useCallback(async () => {
    if (!window.confirm("Operator Terminalを停止しますか？")) {
      return;
    }
    setOperatorPending(true);
    setOperatorError(null);
    try {
      const stopped = await requestJson<OperatorTerminal>(
        "/api/operator-terminal",
        {
          method: "DELETE",
        },
      );
      setOperator(stopped);
      setSelectedTerminal(terminals[0] ? worktreeValue(terminals[0]) : null);
    } catch (requestError) {
      setOperatorError(
        requestError instanceof Error
          ? requestError.message
          : "Operator Terminalを停止できませんでした。",
      );
    } finally {
      setOperatorPending(false);
    }
  }, [terminals]);

  const operatorRunning =
    operator?.state === "on" && operator.operator_id !== null;

  return (
    <OverviewFrame className="terminal-frame" collapsed={collapsed}>
      <OverviewSide collapsed={collapsed.left} side="left">
        <WidgetFrame title="Terminal">
          <Group justify="space-between" m="md">
            <Text fw={500}>Operator</Text>
            <Badge color={operatorRunning ? "green" : "gray"}>
              {operatorRunning ? "ON" : "OFF"}
            </Badge>
          </Group>
          <Button
            color={operatorRunning ? "red" : "blue"}
            fullWidth
            loading={operatorPending}
            m="md"
            onClick={operatorRunning ? stopOperator : startOperator}
          >
            {operatorRunning ? "OFF" : "ON"}
          </Button>
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
            terminals.map((worktree, index) => {
              const value = worktreeValue(worktree);
              return (
                <GroupedListRow
                  key={value}
                  onClick={() => setSelectedTerminal(value)}
                  selected={value === selectedTerminal}
                  subtitle={worktree.task_id}
                  title={worktree.parent_project}
                  withDivider={index < terminals.length - 1}
                />
              );
            })
          )}
          {error && (
            <Alert color="red" m="md">
              {error}
            </Alert>
          )}
          {operatorError && (
            <Alert color="red" m="md">
              {operatorError}
            </Alert>
          )}
        </WidgetFrame>
      </OverviewSide>
      <OverviewColumn>
        <WidgetFrame title="Terminal">
          {operatorRunning && selectedTerminal === "operator" ? (
            <TerminalWidget
              endpoint={`/api/operator-terminals/${encodeURIComponent(operator?.operator_id ?? "")}`}
              label="Operator / workspace-hub"
              resizeSignal={`${collapsed.left}:${collapsed.right}`}
            />
          ) : selectedWorktree ? (
            <TerminalWidget
              project={selectedWorktree.parent_project}
              resizeSignal={`${collapsed.left}:${collapsed.right}`}
              taskId={selectedWorktree.task_id}
            />
          ) : (
            <Text c="dimmed" p="md">
              表示できる端末はありません。
            </Text>
          )}
        </WidgetFrame>
      </OverviewColumn>
      <OverviewSide collapsed={collapsed.right} side="right">
        <WidgetFrame title="Session">
          <Text c="dimmed" p="md">
            Session情報は後続のPhaseで追加します。
          </Text>
        </WidgetFrame>
        <WidgetFrame title="Activity">
          <Text c="dimmed" p="md">
            Activity情報は後続のPhaseで追加します。
          </Text>
        </WidgetFrame>
      </OverviewSide>
    </OverviewFrame>
  );
}
