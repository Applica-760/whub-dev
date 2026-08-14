import { useCallback } from "react";
import { useLocation, useNavigate } from "react-router";

import { TerminalExplorerPage } from "../explorer/TerminalExplorerPage";
import type { TerminalCollapseState } from "./useTerminalCollapse";
import { TerminalWorkspace } from "./workspace/TerminalWorkspace";

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

  return (
    <>
      <div hidden={explorer}>
        <TerminalWorkspace
          collapsed={collapsed}
          explorer={explorer}
          onToggleExplorer={toggleExplorer}
        />
      </div>
      <div hidden={!explorer}>
        <TerminalExplorerPage />
      </div>
    </>
  );
}
