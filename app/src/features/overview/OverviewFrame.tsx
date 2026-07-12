import type { ReactNode } from 'react';

import './overview.css';

type OverviewFrameProps = {
  children: ReactNode;
};

type OverviewColumnProps = {
  children: ReactNode;
};

export function OverviewFrame({ children }: OverviewFrameProps) {
  return <main className="overview-frame">{children}</main>;
}

export function OverviewColumn({ children }: OverviewColumnProps) {
  return <div className="overview-column">{children}</div>;
}
