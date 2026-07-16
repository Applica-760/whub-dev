import { Alert, Box, Text } from '@mantine/core';
import { useCallback, useEffect, useState } from 'react';

import { errorMessage } from '../../api/errorMessage';
import { MermaidDiagram } from '../../components/MermaidDiagram';
import { WidgetFrame } from '../../components/WidgetFrame';
import { getTaskFlowGraph } from './api';

type TaskFlowGraphWidgetProps = {
  taskId: string;
};

export function TaskFlowGraphWidget({ taskId }: TaskFlowGraphWidgetProps) {
  const [chart, setChart] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadGraph = useCallback(async () => {
    setError(null);
    try {
      setChart((await getTaskFlowGraph(taskId)).mermaid);
    } catch (requestError) {
      setError(errorMessage(requestError));
    }
  }, [taskId]);

  useEffect(() => {
    void loadGraph();
  }, [loadGraph]);

  return (
    <WidgetFrame title={<Text c="dimmed" fw={600} size="sm">Task flow</Text>}>
      <Box p="md">
        {error ? (
          <Alert color="red" title="Taskフローを取得できませんでした">{error}</Alert>
        ) : chart ? (
          <MermaidDiagram chart={chart} />
        ) : (
          <Text c="dimmed">Taskフローを読み込んでいます…</Text>
        )}
      </Box>
    </WidgetFrame>
  );
}
