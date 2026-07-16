import { Stack } from '@mantine/core';

import { PageFrame } from '../../components/PageFrame';
import { TaskDependencyGraphWidget } from './TaskDependencyGraphWidget';
import { TaskWidget } from './TaskWidget';

export function TasksPage() {
  return (
    <PageFrame>
      <Stack gap="md">
        <TaskDependencyGraphWidget />
        <TaskWidget />
      </Stack>
    </PageFrame>
  );
}
