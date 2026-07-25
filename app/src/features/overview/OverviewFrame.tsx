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
  children: ReactNode;
};

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

export function OverviewSide({ side, collapsed, children }: OverviewSideProps) {
  // 折りたたみ中もwidgetをmountしたままにし、入力途中の値と取得済みデータを保つ
  return (
    <div
      className="overview-column"
      data-collapsed={collapsed}
      data-side={side}
    >
      {children}
    </div>
  );
}
