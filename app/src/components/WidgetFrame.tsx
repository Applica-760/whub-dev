import { Group, Paper, Stack, Title } from '@mantine/core';
import type { ReactNode } from 'react';

type WidgetFrameProps = {
  title: ReactNode;
  action?: ReactNode;
  children: ReactNode;
};

export function WidgetFrame({ title, action, children }: WidgetFrameProps) {
  return (
    <Paper h="100%" p="md" radius="md" shadow="xs" withBorder>
      <Stack gap="md">
        <Group justify="space-between" wrap="nowrap">
          <Title order={3}>{title}</Title>
          {action}
        </Group>
        {children}
      </Stack>
    </Paper>
  );
}
