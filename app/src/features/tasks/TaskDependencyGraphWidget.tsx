import { Alert, Box, Text } from '@mantine/core';

import { TaskDependencyGraph } from '../../components/TaskDependencyGraph';
import { WidgetFrame } from '../../components/WidgetFrame';
import { useTasks } from './useTasks';

type TaskDependencyGraphWidgetProps = {
  height?: number;
};

export function TaskDependencyGraphWidget({ height }: TaskDependencyGraphWidgetProps) {
  const { tasks, loading, error } = useTasks();

  return (
    <WidgetFrame title={<Text c="dimmed" fw={600} size="sm">Task dependencies</Text>}>
      <Box p="md">
        {error ? (
          <Alert color="red" title="Taskグラフを取得できませんでした">{error}</Alert>
        ) : loading ? (
          <Text c="dimmed">Taskグラフを読み込んでいます…</Text>
        ) : (
          <TaskDependencyGraph height={height} tasks={tasks} />
        )}
      </Box>
    </WidgetFrame>
  );
}
