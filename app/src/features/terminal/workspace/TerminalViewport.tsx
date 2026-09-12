import { Text } from "@mantine/core";

import { TerminalWidgetFrame } from "../../../components/TerminalWidgetFrame";
import { TerminalWidget } from "../TerminalWidget";
import type { TerminalCollapseState } from "../useTerminalCollapse";
import type { TerminalTarget } from "./terminalTarget";

type TerminalViewportProps = {
  collapsed: TerminalCollapseState;
  explorer: boolean;
  mountedValues: string[];
  reloads: Record<string, number>;
  selectedValue: string | null;
  targets: TerminalTarget[];
};

export function TerminalViewport({
  collapsed,
  explorer,
  mountedValues,
  reloads,
  selectedValue,
  targets,
}: TerminalViewportProps) {
  return (
    <TerminalWidgetFrame>
      {targets.length ? (
        targets.map((target) => {
          const active = !explorer && target.value === selectedValue;
          if (!active && !mountedValues.includes(target.value)) return null;
          const connection =
            target.kind === "operator"
              ? {
                  endpoint: `/api/operator-terminals/${encodeURIComponent(target.operatorId)}`,
                }
              : { project: target.project, issueNumber: target.issueNumber };
          return (
            <div hidden={!active} key={target.value} style={{ height: "100%" }}>
              <TerminalWidget
                {...connection}
                active={active}
                key={reloads[target.value] ?? 0}
                resizeSignal={`${target.value}:${active}:${collapsed.left}:${collapsed.right}:${explorer}`}
              />
            </div>
          );
        })
      ) : (
        <Text c="dimmed" p="md">
          表示できる端末はありません。
        </Text>
      )}
    </TerminalWidgetFrame>
  );
}
