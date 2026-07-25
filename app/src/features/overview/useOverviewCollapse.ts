import { useLocalStorage } from "@mantine/hooks";
import { useCallback } from "react";

export const OVERVIEW_COLLAPSE_KEY = "whub.overview.collapsed";

export type OverviewSideName = "left" | "right";

export type OverviewCollapseState = Record<OverviewSideName, boolean>;

const DEFAULT_STATE: OverviewCollapseState = { left: false, right: false };

// 壊れた保存値やスキーマ変更でundefinedの列が生まれないよう、両側展開へ寄せる
function normalize(value: unknown): OverviewCollapseState {
  if (typeof value !== "object" || value === null) {
    return DEFAULT_STATE;
  }

  const record = value as Partial<Record<OverviewSideName, unknown>>;
  return { left: record.left === true, right: record.right === true };
}

export function useOverviewCollapse() {
  const [collapsed, setCollapsed] = useLocalStorage<OverviewCollapseState>({
    key: OVERVIEW_COLLAPSE_KEY,
    defaultValue: DEFAULT_STATE,
    // SSRしないSPAなので、初回描画から保存値を反映して列幅のちらつきを避ける
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
    (side: OverviewSideName) => {
      setCollapsed((current) => {
        const state = normalize(current);
        return { ...state, [side]: !state[side] };
      });
    },
    [setCollapsed],
  );

  return { collapsed, toggle };
}
