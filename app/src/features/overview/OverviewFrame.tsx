import { ActionIcon } from "@mantine/core";
import {
  IconLayoutSidebarLeftCollapse,
  IconLayoutSidebarLeftExpand,
  IconLayoutSidebarRightCollapse,
  IconLayoutSidebarRightExpand,
} from "@tabler/icons-react";
import type { ReactNode } from "react";

import type {
  OverviewCollapseState,
  OverviewSideName,
} from "./useOverviewCollapse";

import "./overview.css";

type OverviewFrameProps = {
  collapsed: OverviewCollapseState;
  children: ReactNode;
};

type OverviewColumnProps = {
  children: ReactNode;
};

type OverviewWideProps = {
  children: ReactNode;
};

type OverviewSideProps = {
  side: OverviewSideName;
  collapsed: boolean;
  onToggle: () => void;
  children: ReactNode;
};

const SIDE_LABEL: Record<OverviewSideName, string> = {
  left: "左サイド",
  right: "右サイド",
};

const SIDE_ICON = {
  left: {
    collapse: IconLayoutSidebarLeftCollapse,
    expand: IconLayoutSidebarLeftExpand,
  },
  right: {
    collapse: IconLayoutSidebarRightCollapse,
    expand: IconLayoutSidebarRightExpand,
  },
} as const;

export function OverviewFrame({ collapsed, children }: OverviewFrameProps) {
  return (
    <main
      className="overview-frame"
      data-collapse-left={collapsed.left}
      data-collapse-right={collapsed.right}
    >
      {children}
    </main>
  );
}

export function OverviewWide({ children }: OverviewWideProps) {
  return <div className="overview-wide">{children}</div>;
}

export function OverviewColumn({ children }: OverviewColumnProps) {
  return <div className="overview-column">{children}</div>;
}

export function OverviewSide({
  side,
  collapsed,
  onToggle,
  children,
}: OverviewSideProps) {
  const Icon = SIDE_ICON[side][collapsed ? "expand" : "collapse"];
  const label = `${SIDE_LABEL[side]}を${collapsed ? "展開する" : "折りたたむ"}`;

  return (
    <div className="overview-side" data-collapsed={collapsed} data-side={side}>
      <div className="overview-side-toggle-row">
        <ActionIcon
          aria-expanded={!collapsed}
          aria-label={label}
          onClick={onToggle}
          size="sm"
          title={label}
          variant="subtle"
        >
          <Icon aria-hidden size={18} stroke={1.5} />
        </ActionIcon>
      </div>
      {/* 折りたたみ中もwidgetをmountしたままにし、入力途中の値と取得済みデータを保つ */}
      <div className="overview-side-body">{children}</div>
    </div>
  );
}
