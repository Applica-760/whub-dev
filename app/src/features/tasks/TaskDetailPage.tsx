import { Alert, Anchor, Box, Stack, Text } from '@mantine/core';
import { useCallback, useEffect, useState } from 'react';
import { NavLink, useParams } from 'react-router';

import type { TaskResponse } from '../../api/client';
import { errorMessage } from '../../api/errorMessage';
import { PageFrame } from '../../components/PageFrame';
import { WidgetFrame } from '../../components/WidgetFrame';
import { getTask } from './api';
import { TaskFlowGraphWidget } from './TaskFlowGraphWidget';

function stepMarker(state: string | null | undefined): string {
  return { done: 'x', skipped: '-' }[state ?? ''] ?? ' ';
}

export function TaskDetailPage() {
  const { taskId } = useParams();
  const [task, setTask] = useState<TaskResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadTask = useCallback(async () => {
    if (!taskId) {
      setError('Task IDがありません');
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      setTask(await getTask(taskId));
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setLoading(false);
    }
  }, [taskId]);

  useEffect(() => {
    void loadTask();
  }, [loadTask]);

  const phases = task?.plan?.phases ?? [];

  return (
    <PageFrame>
      <Stack gap="md">
        {taskId && <TaskFlowGraphWidget taskId={taskId} />}
        <WidgetFrame
          action={<Anchor component={NavLink} size="sm" to="/tasks">一覧へ戻る</Anchor>}
          title={<Text c="dimmed" fw={600} size="sm">{task?.task?.title ?? 'Task'}</Text>}
        >
          <Box p="md">
            {error ? (
              <Alert color="red" title="Taskを取得できませんでした">{error}</Alert>
            ) : loading ? (
              <Text c="dimmed">Taskを読み込んでいます…</Text>
            ) : task ? (
              <Stack gap="md">
                <Text>state: {task.task?.state ?? '-'}</Text>
                {(task.task?.approach ?? []).length > 0 && (
                  <Stack gap={2}>
                    <Text fw={600}>Approach</Text>
                    {(task.task?.approach ?? []).map((item, index) => (
                      <Text key={`${index}-${item}`} pl="md" size="sm">- {item}</Text>
                    ))}
                  </Stack>
                )}
                {task.plan ? phases.map((phase, phaseIndex) => (
                  <Stack gap="xs" key={`${phaseIndex}-${phase.title}`}>
                    <Text fw={600}>Phase {phaseIndex + 1}: {phase.title}</Text>
                    {(phase.steps ?? []).map((step, stepIndex) => (
                      <Stack gap={0} key={`${stepIndex}-${step.description}`}>
                        <Text pl="xl">[{stepMarker(step.state)}] {step.description}</Text>
                        {step.skip_reason && <Text c="dimmed" pl="md" size="sm">- skipped: {step.skip_reason}</Text>}
                      </Stack>
                    ))}
                    {(phase.log ?? []).map((item, logIndex) => (
                      <Text c="dimmed" key={`${logIndex}-${item}`} pl="md" size="sm">- {item}</Text>
                    ))}
                  </Stack>
                )) : <Text c="dimmed">plan: -</Text>}
              </Stack>
            ) : null}
          </Box>
        </WidgetFrame>
      </Stack>
    </PageFrame>
  );
}
