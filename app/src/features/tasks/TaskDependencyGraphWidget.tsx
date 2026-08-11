import { Alert, Box, Text } from "@mantine/core";
import { useCallback } from "react";
import type { CSSProperties } from "react";
import { useNavigate } from "react-router";

import { TaskDependencyGraph } from "../../components/TaskDependencyGraph";
import { WidgetFrame } from "../../components/WidgetFrame";
import { taskDetailPath } from "./routes";
import { useTasks } from "./useTasks";

type TaskDependencyGraphWidgetProps = {
  project: string | null;
  height?: CSSProperties["height"];
  onSelectTask?: (project: string, taskId: string) => void;
  active?: boolean;
  hideTitle?: boolean;
};

export function TaskDependencyGraphWidget({
  project,
  height,
  onSelectTask,
  active = false,
  hideTitle = false,
}: TaskDependencyGraphWidgetProps) {
  const { tasks, loading, error } = useTasks(project, active);
  const navigate = useNavigate();
  const handleSelectTask = useCallback(
    (taskId: string) => {
      if (!project) {
        return;
      }
      if (onSelectTask) {
        onSelectTask(project, taskId);
        return;
      }
      void navigate(taskDetailPath(project, taskId));
    },
    [navigate, onSelectTask, project],
  );

  return (
    <WidgetFrame
      title={
        hideTitle ? undefined : (
          <Text c="dimmed" fw={600} size="sm">
            Task dependencies
          </Text>
        )
      }
    >
      <Box h="100%" p="md">
        {error ? (
          <Alert color="red" title="Taskグラフを取得できませんでした">
            {error}
          </Alert>
        ) : loading ? (
          <Text c="dimmed">Taskグラフを読み込んでいます…</Text>
        ) : !project ? (
          <Text c="dimmed">表示するProjectを選択してください</Text>
        ) : (
          <TaskDependencyGraph
            height={height}
            onSelectTask={handleSelectTask}
            tasks={tasks}
          />
        )}
      </Box>
    </WidgetFrame>
  );
}
