import { Anchor, AppShell, Center, Group, Loader, Text } from '@mantine/core';
import { lazy, Suspense } from 'react';
import { NavLink, Route, Routes, useLocation } from 'react-router';

import { InboxPage } from './features/inbox/InboxPage';
import { OverviewPage } from './features/overview/OverviewPage';
import { ResourceStatusPage } from './features/status/ResourceStatusPage';
import { TodosPage } from './features/todos/TodosPage';

// react-markdownの依存ツリーを初回チャンクから外すため、Backlog/Vaultは遅延読込する
const BacklogPage = lazy(() =>
  import('./features/backlog/BacklogPage').then((module) => ({ default: module.BacklogPage })),
);
const VaultPage = lazy(() =>
  import('./features/vault/VaultPage').then((module) => ({ default: module.VaultPage })),
);

const navigation = [
  { label: 'Overview', to: '/' },
  { label: 'Todo', to: '/todos' },
  { label: 'Backlog', to: '/backlog' },
  { label: 'Inbox', to: '/inbox' },
  { label: 'Vault', to: '/vault' },
  { label: 'Status', to: '/status' },
];

export function App() {
  const location = useLocation();

  return (
    <AppShell header={{ height: 47 }} padding={0}>
      <AppShell.Header className="whub-header">
        <Group align="end" gap="xl" h="100%" px="md">
          <Text fw={700} pb={10}>whub</Text>
          <div className="whub-tabs">
            {navigation.map((item) => (
              <Anchor
                aria-current={location.pathname === item.to ? 'page' : undefined}
                className="whub-tab"
                component={NavLink}
                data-active={location.pathname === item.to}
                key={item.to}
                to={item.to}
              >
                {item.label}
              </Anchor>
            ))}
          </div>
        </Group>
      </AppShell.Header>

      <AppShell.Main style={{ background: '#f2f2f7', minHeight: '100vh' }}>
        <Suspense
          fallback={
            <Center pt="xl">
              <Loader size="sm" />
            </Center>
          }
        >
          <Routes>
            <Route element={<OverviewPage />} path="/" />
            <Route element={<TodosPage />} path="/todos" />
            <Route element={<BacklogPage />} path="/backlog" />
            <Route element={<VaultPage />} path="/vault" />
            <Route element={<InboxPage />} path="/inbox" />
            <Route element={<ResourceStatusPage />} path="/status" />
          </Routes>
        </Suspense>
      </AppShell.Main>
    </AppShell>
  );
}
