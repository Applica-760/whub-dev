import { useCallback, useEffect, useMemo, useState } from "react";

import type { SelectedTask } from "../../tasks/AllTasksWidget";
import { useAgentSessions } from "../agentSessions";
import { useOperatorTerminals } from "../operatorTerminals";
import { useApprovalAttention } from "../useApprovalAttention";
import {
  targetHasAttention,
  terminalTargets,
  type TerminalTarget,
} from "./terminalTarget";

type TerminalControllerOptions = {
  explorer: boolean;
  onToggleExplorer: () => void;
};

export function useTerminalController({
  explorer,
  onToggleExplorer,
}: TerminalControllerOptions) {
  const { error, loading, sessions } = useAgentSessions();
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
  const targets = useMemo(
    () => terminalTargets(operators, sessions),
    [operators, sessions],
  );
  const [selectedValue, setSelectedValue] = useState<string | null>(null);
  const [mountedValues, setMountedValues] = useState<string[]>([]);
  const [reloads, setReloads] = useState<Record<string, number>>({});
  const [selectedTask, setSelectedTask] = useState<SelectedTask | null>(null);
  const selectedTarget = targets.find(
    (target) => target.value === selectedValue,
  );
  const pendingAttention = attention.filter((item) => !item.acknowledged);
  const taskContext = {
    detailProject:
      selectedTask?.project ??
      (selectedTarget?.kind === "worktree"
        ? selectedTarget.project
        : undefined),
    detailTaskId: selectedTask?.taskId,
    emptyMessage:
      selectedTarget?.kind === "operator"
        ? "グラフからTaskを選択してください"
        : "Terminalを選択してください",
    graphProject: selectedTarget?.taskProject ?? null,
  };

  const acknowledgeTarget = useCallback(
    (target: TerminalTarget) => {
      if (!pendingAttention.some((item) => targetHasAttention(target, item)))
        return;
      if (target.kind === "operator")
        void acknowledgeOperator(target.operatorId);
      else void acknowledgeWorktree(target.project, target.issueNumber);
    },
    [acknowledgeOperator, acknowledgeWorktree, pendingAttention],
  );

  const selectTerminal = useCallback(
    (value: string) => {
      setSelectedValue(value);
      const target = targets.find((item) => item.value === value);
      if (target) acknowledgeTarget(target);
    },
    [acknowledgeTarget, targets],
  );

  const reloadTerminal = useCallback(
    (value: string) => {
      selectTerminal(value);
      setReloads((current) => ({
        ...current,
        [value]: (current[value] ?? 0) + 1,
      }));
    },
    [selectTerminal],
  );

  const selectTask = useCallback((project: string, taskId: string) => {
    setSelectedTask({ project, taskId });
  }, []);

  useEffect(() => setSelectedTask(null), [selectedValue]);

  useEffect(() => {
    if (explorer || !selectedValue) return;
    setMountedValues((current) =>
      current.includes(selectedValue) ? current : [...current, selectedValue],
    );
  }, [explorer, selectedValue]);

  useEffect(() => {
    setSelectedValue((current) => {
      if (explorer && current === null) return null;
      if (!operatorsLoaded) return current;
      if (targets.some((target) => target.value === current)) return current;
      const operator = targets.find((target) => target.kind === "operator");
      if (operator) return operator.value;
      if (loading) return current;
      return targets[0]?.value ?? null;
    });
  }, [explorer, loading, operatorsLoaded, targets]);

  useEffect(() => {
    const onVisibilityChange = () => {
      if (document.visibilityState === "visible" && selectedTarget)
        acknowledgeTarget(selectedTarget);
    };
    document.addEventListener("visibilitychange", onVisibilityChange);
    return () =>
      document.removeEventListener("visibilitychange", onVisibilityChange);
  }, [acknowledgeTarget, selectedTarget]);

  const startOperator = useCallback(async () => {
    const created = await createOperator();
    if (created) setSelectedValue(`operator/${created.operator_id}`);
  }, [createOperator]);

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
        if (selectedTarget?.kind === "operator" && !operatorPending) {
          event.preventDefault();
          void stopOperator(selectedTarget.operatorId);
        }
        return;
      }
      if (
        !targets.length ||
        (event.key !== "ArrowUp" && event.key !== "ArrowDown")
      )
        return;
      event.preventDefault();
      const index = targets.findIndex(
        (target) => target.value === selectedValue,
      );
      const nextIndex =
        event.key === "ArrowDown"
          ? (index + 1 + targets.length) % targets.length
          : index <= 0
            ? targets.length - 1
            : index - 1;
      selectTerminal(targets[nextIndex].value);
    };
    window.addEventListener("keydown", onKeyDown, true);
    return () => window.removeEventListener("keydown", onKeyDown, true);
  }, [
    onToggleExplorer,
    operatorPending,
    selectedTarget,
    selectedValue,
    selectTerminal,
    startOperator,
    stopOperator,
    targets,
  ]);

  return {
    error: error ?? operatorError,
    loading,
    mountedValues,
    operatorPending,
    pendingAttention,
    reloads,
    reloadTerminal,
    selectedTarget,
    selectedTask,
    selectedValue,
    selectTask,
    selectTerminal,
    startOperator,
    stopOperator,
    taskContext,
    targets,
  };
}
