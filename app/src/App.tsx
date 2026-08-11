import { Anchor, AppShell, Center, Group, Loader, Text } from "@mantine/core";
import { lazy, Suspense } from "react";
import { NavLink, Route, Routes, useLocation } from "react-router";

import { ColorSchemeToggle } from "./components/ColorSchemeToggle";
import { InboxPage } from "./features/inbox/InboxPage";
import { OverviewCollapseToggles } from "./features/overview/OverviewCollapseToggles";
import { OverviewPage } from "./features/overview/OverviewPage";
import { useOverviewCollapse } from "./features/overview/useOverviewCollapse";
import { ResourceStatusPage } from "./features/status/ResourceStatusPage";
import { TerminalPage } from "./features/terminal/TerminalPage";
import { useTerminalCollapse } from "./features/terminal/useTerminalCollapse";
import { TaskDetailPage } from "./features/tasks/TaskDetailPage";
import { TasksPage } from "./features/tasks/TasksPage";
import {
  isTasksRoute,
  LEGACY_TASK_DETAIL_PATH,
  TASK_DETAIL_PATH,
  TASKS_PATH,
} from "./features/tasks/routes";
import { TodosPage } from "./features/todos/TodosPage";

// react-markdownの依存ツリーを初回チャンクから外すため、Backlog/Vaultは遅延読込する
const BacklogPage = lazy(() =>
  import("./features/backlog/BacklogPage").then((module) => ({
    default: module.BacklogPage,
  })),
);
const VaultPage = lazy(() =>
  import("./features/vault/VaultPage").then((module) => ({
    default: module.VaultPage,
  })),
);

type NavigationItem = {
  label: string;
  to: string;
  isActive?: (pathname: string) => boolean;
};

const OVERVIEW_PATH = "/";
const TERMINAL_PATH = "/terminal";

const navigation: NavigationItem[] = [
  { label: "Overview", to: OVERVIEW_PATH },
  {
    label: "Terminal",
    to: TERMINAL_PATH,
    isActive: (pathname) =>
      pathname === TERMINAL_PATH || pathname.startsWith(`${TERMINAL_PATH}/`),
  },
  { label: "Task", to: TASKS_PATH, isActive: isTasksRoute },
  { label: "Backlog", to: "/backlog" },
  { label: "Vault", to: "/vault" },
  { label: "Todo", to: "/todos" },
  { label: "Inbox", to: "/inbox" },
  { label: "Status", to: "/status" },
];

export function App() {
  const location = useLocation();
  const overviewCollapse = useOverviewCollapse();
  const terminalCollapse = useTerminalCollapse();

  return (
    <AppShell header={{ height: 40 }} padding={0}>
      <AppShell.Header className="whub-header">
        <Group align="end" gap="xl" h="100%" px="md" wrap="nowrap">
          <Text fw={700} pb={10}>
            whub
          </Text>
          <div className="whub-tabs">
            {navigation.map((item) => {
              const active =
                item.isActive?.(location.pathname) ??
                location.pathname === item.to;

              return (
                <Anchor
                  aria-current={active ? "page" : undefined}
                  className="whub-tab"
                  component={NavLink}
                  data-active={active}
                  key={item.to}
                  to={item.to}
                >
                  {item.label}
                </Anchor>
              );
            })}
          </div>
          <div className="whub-header-actions">
            {location.pathname === OVERVIEW_PATH && (
              <OverviewCollapseToggles
                collapsed={overviewCollapse.collapsed}
                onToggle={overviewCollapse.toggle}
              />
            )}
            {location.pathname.startsWith(TERMINAL_PATH) && (
              <OverviewCollapseToggles
                collapsed={terminalCollapse.collapsed}
                onToggle={terminalCollapse.toggle}
                sideLabels={{ left: "Explorer", right: "Task" }}
                sides={["left", "right"]}
              />
            )}
            <ColorSchemeToggle />
          </div>
        </Group>
      </AppShell.Header>

      <AppShell.Main className="whub-main">
        <Suspense
          fallback={
            <Center pt="xl">
              <Loader size="sm" />
            </Center>
          }
        >
          <Routes>
            <Route
              element={<OverviewPage collapsed={overviewCollapse.collapsed} />}
              path={OVERVIEW_PATH}
            />
            <Route element={<BacklogPage />} path="/backlog" />
            <Route element={<VaultPage />} path="/vault" />
            <Route element={<TodosPage />} path="/todos" />
            <Route
              element={<TerminalPage collapsed={terminalCollapse.collapsed} />}
              path={`${TERMINAL_PATH}/*`}
            />
            <Route element={<TasksPage />} path="/tasks" />
            <Route element={<TaskDetailPage />} path={TASK_DETAIL_PATH} />
            <Route
              element={<TaskDetailPage />}
              path={LEGACY_TASK_DETAIL_PATH}
            />
            <Route element={<InboxPage />} path="/inbox" />
            <Route element={<ResourceStatusPage />} path="/status" />
          </Routes>
        </Suspense>
      </AppShell.Main>
    </AppShell>
  );
}
