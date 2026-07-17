import { Anchor, AppShell, Center, Group, Loader, Text } from '@mantine/core';
import { lazy, Suspense } from 'react';
import { NavLink, Route, Routes, useLocation } from 'react-router';

import { ColorSchemeToggle } from './components/ColorSchemeToggle';
import { InboxPage } from './features/inbox/InboxPage';
import { KnowledgePage } from './features/knowledge/KnowledgePage';
import { OverviewPage } from './features/overview/OverviewPage';
import { ResourceStatusPage } from './features/status/ResourceStatusPage';
import { TaskDetailPage } from './features/tasks/TaskDetailPage';
import { TasksPage } from './features/tasks/TasksPage';
import { isTasksRoute, TASKS_PATH } from './features/tasks/routes';
import { TodosPage } from './features/todos/TodosPage';

// react-markdownの依存ツリーを初回チャンクから外すため、Backlog/Vaultは遅延読込する
const BacklogPage = lazy(() =>
  import('./features/backlog/BacklogPage').then((module) => ({ default: module.BacklogPage })),
);
const VaultPage = lazy(() =>
  import('./features/vault/VaultPage').then((module) => ({ default: module.VaultPage })),
);

type NavigationItem = {
  label: string;
  to: string;
  isActive?: (pathname: string) => boolean;
};

const navigation: NavigationItem[] = [
  { label: 'Overview', to: '/' },
  { label: 'Backlog', to: '/backlog' },
  { label: 'Vault', to: '/vault' },
  { label: 'Knowledge', to: '/knowledge' },
  { label: 'Todo', to: '/todos' },
  { label: 'Task', to: TASKS_PATH, isActive: isTasksRoute },
  { label: 'Inbox', to: '/inbox' },
  { label: 'Status', to: '/status' },
];

export function App() {
  const location = useLocation();

  return (
    <AppShell header={{ height: 47 }} padding={0}>
      <AppShell.Header className="whub-header">
        <Group align="end" gap="xl" h="100%" px="md" wrap="nowrap">
          <Text fw={700} pb={10}>whub</Text>
          <div className="whub-tabs">
            {navigation.map((item) => {
              const active = item.isActive?.(location.pathname) ?? location.pathname === item.to;

              return (
                <Anchor
                  aria-current={active ? 'page' : undefined}
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
          <ColorSchemeToggle />
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
            <Route element={<OverviewPage />} path="/" />
            <Route element={<BacklogPage />} path="/backlog" />
            <Route element={<KnowledgePage />} path="/knowledge" />
            <Route element={<VaultPage />} path="/vault" />
            <Route element={<TodosPage />} path="/todos" />
            <Route element={<TasksPage />} path="/tasks" />
            <Route element={<TaskDetailPage />} path="/tasks/:taskId" />
            <Route element={<InboxPage />} path="/inbox" />
            <Route element={<ResourceStatusPage />} path="/status" />
          </Routes>
        </Suspense>
      </AppShell.Main>
    </AppShell>
  );
}
