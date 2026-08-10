import { Alert, Box, Stack, Text } from "@mantine/core";
import { useCallback, useEffect, useState } from "react";
import type { ReactNode } from "react";

import type { TaskResponse } from "../../api/client";
import { errorMessage } from "../../api/errorMessage";
import { MarkdownView } from "../../components/MarkdownView";
import { WidgetFrame } from "../../components/WidgetFrame";
import { getTask, listTasks } from "./api";

type TaskDetailWidgetProps = {
  taskId?: string | null;
  project?: string | null;
  action?: ReactNode;
  emptyMessage?: string;
};

export function TaskDetailWidget({
  taskId,
  project,
  action,
  emptyMessage = "Taskを選択してください",
}: TaskDetailWidgetProps) {
  const [task, setTask] = useState<TaskResponse | null>(null);
  const [dependents, setDependents] = useState<string[]>([]);
  const [loading, setLoading] = useState(Boolean(taskId));
  const [error, setError] = useState<string | null>(null);

  const loadTask = useCallback(async () => {
    setTask(null);
    setDependents([]);
    setError(null);
    if (!taskId) {
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const [loadedTask, taskList] = await Promise.all([
        getTask(taskId, project),
        listTasks(project),
      ]);
      setTask(loadedTask);
      setDependents(
        taskList.tasks
          .flatMap((item) =>
            item.id != null && (item.depends_on ?? []).includes(taskId)
              ? [item.id]
              : [],
          )
          .sort(),
      );
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setLoading(false);
    }
  }, [project, taskId]);

  useEffect(() => {
    void loadTask();
  }, [loadTask]);

  return (
    <WidgetFrame
      action={action}
      title={
        <Text c="dimmed" fw={600} size="sm">
          {task?.title ?? task?.task?.id ?? "Task"}
        </Text>
      }
    >
      <Box p="md">
        {!taskId ? (
          <Text c="dimmed">{emptyMessage}</Text>
        ) : error ? (
          <Alert color="red" title="Taskを取得できませんでした">
            {error}
          </Alert>
        ) : loading ? (
          <Text c="dimmed">Taskを読み込んでいます…</Text>
        ) : task ? (
          <Stack gap="md">
            <Text>{`${task.task?.id ?? "-"}(${task.task?.state ?? "-"})`}</Text>
            {Boolean(task.task?.depends_on?.length || dependents.length) && (
              <Text>
                {[
                  (task.task?.depends_on ?? []).join(", "),
                  task.task?.id ?? "-",
                  dependents.join(", "),
                ]
                  .filter(Boolean)
                  .map((ids) => `(${ids})`)
                  .join(" -> ")}
              </Text>
            )}
            <MarkdownView content={task.markdown ?? ""} />
          </Stack>
        ) : null}
      </Box>
    </WidgetFrame>
  );
}
