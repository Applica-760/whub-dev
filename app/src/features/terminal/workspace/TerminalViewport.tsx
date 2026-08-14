import { Text } from "@mantine/core";

import { TerminalWidgetFrame } from "../../../components/TerminalWidgetFrame";
import type { AgentSession } from "../agentSessions";
import type { OperatorTerminal } from "../operatorTerminals";
import { TerminalWidget } from "../TerminalWidget";
import type { TerminalCollapseState } from "../useTerminalCollapse";
import { operatorValue, worktreeValue } from "./terminalValue";

type TerminalViewportProps = {
  collapsed: TerminalCollapseState;
  explorer: boolean;
  mountedTerminals: string[];
  operators: OperatorTerminal[];
  selectedTerminal: string | null;
  terminalReloads: Record<string, number>;
  terminals: AgentSession[];
};

export function TerminalViewport({
  collapsed,
  explorer,
  mountedTerminals,
  operators,
  selectedTerminal,
  terminalReloads,
  terminals,
}: TerminalViewportProps) {
  return (
    <TerminalWidgetFrame>
      {operators.length || terminals.length ? (
        <>
          {operators.map((operator) => {
            const value = operatorValue(operator.operator_id);
            const active = !explorer && value === selectedTerminal;
            if (!active && !mountedTerminals.includes(value)) return null;
            return (
              <div hidden={!active} key={value} style={{ height: "100%" }}>
                <TerminalWidget
                  active={active}
                  endpoint={`/api/operator-terminals/${encodeURIComponent(operator.operator_id)}`}
                  key={terminalReloads[value] ?? 0}
                  resizeSignal={`${value}:${active}:${collapsed.left}:${collapsed.right}:${explorer}`}
                />
              </div>
            );
          })}
          {terminals.map((worktree) => {
            const value = worktreeValue(worktree);
            const active = !explorer && value === selectedTerminal;
            if (!active && !mountedTerminals.includes(value)) return null;
            return (
              <div hidden={!active} key={value} style={{ height: "100%" }}>
                <TerminalWidget
                  active={active}
                  key={terminalReloads[value] ?? 0}
                  project={worktree.project}
                  resizeSignal={`${value}:${active}:${collapsed.left}:${collapsed.right}:${explorer}`}
                  taskId={worktree.task_id}
                />
              </div>
            );
          })}
        </>
      ) : (
        <Text c="dimmed" p="md">
          表示できる端末はありません。
        </Text>
      )}
    </TerminalWidgetFrame>
  );
}
