import { useLocalStorage } from "@mantine/hooks";
import { useCallback } from "react";

export const TERMINAL_COLLAPSE_KEY = "whub.terminal.collapsed";

export type TerminalSideName = "left" | "right";

export type TerminalCollapseState = Record<TerminalSideName, boolean>;

const DEFAULT_STATE: TerminalCollapseState = { left: false, right: false };

function normalize(value: unknown): TerminalCollapseState {
  if (typeof value !== "object" || value === null) {
    return DEFAULT_STATE;
  }

  const record = value as Partial<Record<TerminalSideName, unknown>>;
  return { left: record.left === true, right: record.right === true };
}

export function useTerminalCollapse() {
  const [collapsed, setCollapsed] = useLocalStorage<TerminalCollapseState>({
    key: TERMINAL_COLLAPSE_KEY,
    defaultValue: DEFAULT_STATE,
    getInitialValueInEffect: false,
    deserialize: (raw) => {
      if (!raw) {
        return DEFAULT_STATE;
      }
      try {
        return normalize(JSON.parse(raw));
      } catch {
        return DEFAULT_STATE;
      }
    },
  });

  const toggle = useCallback(
    (side: TerminalSideName) => {
      setCollapsed((current) => {
        const state = normalize(current);
        return { ...state, [side]: !state[side] };
      });
    },
    [setCollapsed],
  );

  return { collapsed, toggle };
}
