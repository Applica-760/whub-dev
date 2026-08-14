import { useCallback, useEffect, useMemo, useState } from "react";

import type { SelectedTask } from "../../tasks/AllTasksWidget";
import { useAgentSessions } from "../agentSessions";
import { useOperatorTerminals } from "../operatorTerminals";
import { useApprovalAttention } from "../useApprovalAttention";
import type { TerminalCollapseState } from "../useTerminalCollapse";
import { TerminalListPanel } from "./TerminalListPanel";
import { TerminalTaskPanel } from "./TerminalTaskPanel";
import { TerminalViewport } from "./TerminalViewport";
import { operatorValue, worktreeValue } from "./terminalValue";

type TerminalWorkspaceProps = {
  collapsed: TerminalCollapseState;
  explorer: boolean;
  onToggleExplorer: () => void;
};

export function TerminalWorkspace({
  collapsed,
  explorer,
  onToggleExplorer,
}: TerminalWorkspaceProps) {
  const { error, loading, sessions: terminals } = useAgentSessions();
  const {
    error: operatorError,
    loaded: operatorsLoaded,
    operators,
    pending: operatorPending,
    startOperator: createOperator,
    stopOperator: removeOperator,
  } = useOperatorTerminals();
  const { acknowledgeOperator, acknowledgeWorktree, attention } =
    useApprovalAttention();
  const [selectedTerminal, setSelectedTerminal] = useState<string | null>(null);
  const [mountedTerminals, setMountedTerminals] = useState<string[]>([]);
  const [terminalReloads, setTerminalReloads] = useState<
    Record<string, number>
  >({});
  const [selectedOperationTask, setSelectedOperationTask] =
    useState<SelectedTask | null>(null);
  const selectedWorktree = terminals.find(
    (item) => worktreeValue(item) === selectedTerminal,
  );
  const pendingAttention = attention.filter((item) => !item.acknowledged);
  const selectedOperator = operators.find(
    (operator) => operatorValue(operator.operator_id) === selectedTerminal,
  );

  const acknowledgeTerminal = useCallback(
    (value: string) => {
      const worktree = terminals.find((item) => worktreeValue(item) === value);
      if (!worktree) return;
      const item = pendingAttention.find(
        (attentionItem) =>
          attentionItem.target === "worktree" &&
          attentionItem.project === worktree.project &&
          attentionItem.task_id === worktree.task_id,
      );
      if (item) void acknowledgeWorktree(worktree.project, worktree.task_id);
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

  const reloadTerminal = useCallback(
    (value: string) => {
      selectTerminal(value);
      setTerminalReloads((current) => ({
        ...current,
        [value]: (current[value] ?? 0) + 1,
      }));
    },
    [selectTerminal],
  );

  const selectOperationTask = useCallback((project: string, taskId: string) => {
    setSelectedOperationTask({ project, taskId });
  }, []);

  useEffect(() => setSelectedOperationTask(null), [selectedTerminal]);

  useEffect(() => {
    if (explorer || !selectedTerminal) return;
    setMountedTerminals((current) =>
      current.includes(selectedTerminal)
        ? current
        : [...current, selectedTerminal],
    );
  }, [explorer, selectedTerminal]);

  useEffect(() => {
    setSelectedTerminal((current) => {
      if (explorer && current === null) return null;
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
  }, [explorer, loading, operators, operatorsLoaded, terminals]);

  useEffect(() => {
    const acknowledgeSelected = () => {
      if (selectedOperator)
        void acknowledgeOperator(selectedOperator.operator_id);
      else if (selectedWorktree)
        void acknowledgeWorktree(
          selectedWorktree.project,
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

  const startOperator = useCallback(async () => {
    const created = await createOperator();
    if (created) openOperator(created.operator_id);
  }, [createOperator, openOperator]);

  const stopOperator = useCallback(
    async (operatorId: string) => {
      if (!window.confirm("Operationを終了しますか？")) return;
      await removeOperator(operatorId);
    },
    [removeOperator],
  );

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (!event.metaKey || !event.shiftKey || event.altKey || event.ctrlKey)
        return;

      if (event.code === "KeyO") {
        if (!operatorPending) {
          event.preventDefault();
          void startOperator();
        }
        return;
      }
      if (event.code === "KeyE") {
        event.preventDefault();
        onToggleExplorer();
        return;
      }
      if (!(event.target instanceof Element)) return;
      if (!event.target.closest(".xterm-view")) return;
      if (event.code === "KeyX") {
        if (selectedOperator && !operatorPending) {
          event.preventDefault();
          void stopOperator(selectedOperator.operator_id);
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
    onToggleExplorer,
    operatorPending,
    selectedOperator,
    selectedTerminal,
    selectTerminal,
    startOperator,
    stopOperator,
    terminalValues,
  ]);

  return (
    <main className="terminal-page">
      <section
        className="terminal-layout"
        data-explorer-collapsed={collapsed.left || undefined}
        data-task-collapsed={collapsed.right || undefined}
      >
        <TerminalTaskPanel
          collapsed={collapsed.right}
          onSelectTask={selectOperationTask}
          operatorSelected={Boolean(selectedOperator)}
          selectedTask={selectedOperationTask}
          selectedWorktree={selectedWorktree}
        />
        <TerminalViewport
          collapsed={collapsed}
          explorer={explorer}
          mountedTerminals={mountedTerminals}
          operators={operators}
          selectedTerminal={selectedTerminal}
          terminalReloads={terminalReloads}
          terminals={terminals}
        />
        <TerminalListPanel
          collapsed={collapsed.left}
          error={error ?? operatorError}
          loading={loading}
          onReload={reloadTerminal}
          onSelect={selectTerminal}
          onStartOperator={() => void startOperator()}
          onStopOperator={(operatorId) => void stopOperator(operatorId)}
          operatorPending={operatorPending}
          operators={operators}
          pendingAttention={pendingAttention}
          selectedTerminal={selectedTerminal}
          terminals={terminals}
        />
      </section>
    </main>
  );
}
