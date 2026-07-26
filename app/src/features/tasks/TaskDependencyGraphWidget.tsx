import { Alert, Box, Text } from "@mantine/core";
import { useCallback, useMemo } from "react";
import { useNavigate } from "react-router";

import { TaskDependencyGraph } from "../../components/TaskDependencyGraph";
import { WidgetFrame } from "../../components/WidgetFrame";
import { taskDetailPath } from "./routes";
import { useTasks } from "./useTasks";

type TaskDependencyGraphWidgetProps = {
  project: string | null;
  height?: number;
};

export function TaskDependencyGraphWidget({
  project,
  height,
}: TaskDependencyGraphWidgetProps) {
  const { tasks, loading, error } = useTasks(project);
  const navigate = useNavigate();
  const handleSelectTask = useCallback(
    (selectedProject: string, taskId: string) => {
      void navigate(taskDetailPath(selectedProject, taskId));
    },
    [navigate],
  );
  const graphTasks = useMemo(
    () => tasks.map((task) => ({ ...task, project: project ?? "" })),
    [project, tasks],
  );

  return (
    <WidgetFrame
      title={
        <Text c="dimmed" fw={600} size="sm">
          Task dependencies
        </Text>
      }
    >
      <Box p="md">
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
            tasks={graphTasks}
          />
        )}
      </Box>
    </WidgetFrame>
  );
}
