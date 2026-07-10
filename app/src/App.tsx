import { Anchor, AppShell, Group, Text } from '@mantine/core';
import { Navigate, NavLink, Route, Routes, useLocation } from 'react-router';

import { BacklogPage } from './features/backlog/BacklogPage';
import { TodosPage } from './features/todos/TodosPage';

const navigation = [
  { label: 'Todo', to: '/todos' },
  { label: 'Backlog', to: '/backlog' },
];

export function App() {
  const location = useLocation();

  return (
    <AppShell header={{ height: 56 }} padding="md">
      <AppShell.Header>
        <Group h="100%" justify="space-between" px="md">
          <Text fw={700}>whub</Text>
          <Group gap="md">
            {navigation.map((item) => (
              <Anchor
                c={location.pathname === item.to ? 'blue' : 'dimmed'}
                component={NavLink}
                fw={600}
                key={item.to}
                to={item.to}
                underline="never"
              >
                {item.label}
              </Anchor>
            ))}
          </Group>
        </Group>
      </AppShell.Header>

      <AppShell.Main style={{ background: '#f2f2f7', minHeight: '100vh' }}>
        <Routes>
          <Route element={<Navigate replace to="/todos" />} path="/" />
          <Route element={<TodosPage />} path="/todos" />
          <Route element={<BacklogPage />} path="/backlog" />
        </Routes>
      </AppShell.Main>
    </AppShell>
  );
}
