import { useCallback } from "react";
import { useLocation, useNavigate } from "react-router";

import { TerminalExplorerPage } from "../explorer/TerminalExplorerPage";
import type { TerminalCollapseState } from "./useTerminalCollapse";
import { TerminalListPanel } from "./workspace/TerminalListPanel";
import { TerminalTaskPanel } from "./workspace/TerminalTaskPanel";
import { TerminalViewport } from "./workspace/TerminalViewport";
import { useTerminalController } from "./workspace/useTerminalController";

import "./terminal.css";

type TerminalPageProps = {
  collapsed?: TerminalCollapseState;
};

export function TerminalPage({
  collapsed = { left: false, right: false },
}: TerminalPageProps) {
  const location = useLocation();
  const navigate = useNavigate();
  const explorer = location.pathname === "/terminal/explorer";
  const toggleExplorer = useCallback(
    () => navigate(explorer ? "/terminal" : "/terminal/explorer"),
    [explorer, navigate],
  );
  const terminal = useTerminalController({
    explorer,
    onToggleExplorer: toggleExplorer,
  });

  return (
    <>
      <div hidden={explorer}>
        <main className="terminal-page">
          <section
            className="terminal-layout"
            data-explorer-collapsed={collapsed.left || undefined}
            data-task-collapsed={collapsed.right || undefined}
          >
            <TerminalTaskPanel
              collapsed={collapsed.right}
              {...terminal.taskContext}
              onSelectTask={terminal.selectTask}
            />
            <TerminalViewport
              collapsed={collapsed}
              explorer={explorer}
              mountedValues={terminal.mountedValues}
              reloads={terminal.reloads}
              selectedValue={terminal.selectedValue}
              targets={terminal.targets}
            />
            <TerminalListPanel
              collapsed={collapsed.left}
              error={terminal.error}
              loading={terminal.loading}
              onReload={terminal.reloadTerminal}
              onSelect={terminal.selectTerminal}
              onStartOperator={() => void terminal.startOperator()}
              onStopOperator={(operatorId) =>
                void terminal.stopOperator(operatorId)
              }
              operatorPending={terminal.operatorPending}
              pendingAttention={terminal.pendingAttention}
              selectedValue={terminal.selectedValue}
              targets={terminal.targets}
            />
          </section>
        </main>
      </div>
      <div hidden={!explorer}>
        <TerminalExplorerPage />
      </div>
    </>
  );
}
