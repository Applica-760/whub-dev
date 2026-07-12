import { Group, Paper, Stack } from '@mantine/core';
import type { ReactNode } from 'react';

type WidgetFrameProps = {
  title?: ReactNode;
  action?: ReactNode;
  children: ReactNode;
};

export function WidgetFrame({ title, action, children }: WidgetFrameProps) {
  return (
    <Stack gap={6} h="100%">
      {(title || action) && (
        <Group justify="space-between" px="sm" wrap="nowrap">
          {title}
          {action}
        </Group>
      )}
      <Paper h="100%" radius="md" shadow="xs" withBorder>
        {children}
      </Paper>
    </Stack>
  );
}
