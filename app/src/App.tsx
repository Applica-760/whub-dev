import { Anchor, AppShell, Group, Text } from '@mantine/core';
import { Navigate, NavLink, Route, Routes, useLocation } from 'react-router';

import { BacklogPage } from './features/backlog/BacklogPage';
import { InboxPage } from './features/inbox/InboxPage';
import { TodosPage } from './features/todos/TodosPage';

const navigation = [
  { label: 'Todo', to: '/todos' },
  { label: 'Backlog', to: '/backlog' },
  { label: 'Inbox', to: '/inbox' },
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
        <Routes>
          <Route element={<Navigate replace to="/todos" />} path="/" />
          <Route element={<TodosPage />} path="/todos" />
          <Route element={<BacklogPage />} path="/backlog" />
          <Route element={<InboxPage />} path="/inbox" />
        </Routes>
      </AppShell.Main>
    </AppShell>
  );
}
