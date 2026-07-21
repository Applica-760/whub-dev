import type { ReactNode } from "react";

type PageFrameProps = {
  children: ReactNode;
  aside?: ReactNode;
};

export function PageFrame({ children, aside }: PageFrameProps) {
  return (
    <div className="whub-page-frame">
      {aside && <aside className="whub-page-aside">{aside}</aside>}
      <main className="whub-page-main">{children}</main>
    </div>
  );
}
