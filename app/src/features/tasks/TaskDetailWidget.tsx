import { Alert, Box, Stack, Text } from "@mantine/core";
import { useCallback, useEffect, useState } from "react";
import type { ReactNode } from "react";

import type { TaskResponse } from "../../api/client";
import { errorMessage } from "../../api/errorMessage";
import { WidgetFrame } from "../../components/WidgetFrame";
import { getTask, listTasks } from "./api";

type TaskDetailWidgetProps = {
  taskId?: string | null;
  project?: string | null;
  action?: ReactNode;
  emptyMessage?: string;
};

function stepMarker(state: string | null | undefined): string {
  return { done: "x", skipped: "-" }[state ?? ""] ?? " ";
}

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

  const phases = task?.plan?.phases ?? [];

  return (
    <WidgetFrame
      action={action}
      title={
        <Text c="dimmed" fw={600} size="sm">
          {task?.task?.title ?? "Task"}
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
            {project && <Text>Project: {project}</Text>}
            <Text>Task ID: {task.task?.id ?? "-"}</Text>
            <Text>state: {task.task?.state ?? "-"}</Text>
            <Text>
              Depends on: {(task.task?.depends_on ?? []).join(", ") || "-"}
            </Text>
            <Text>Depended on by: {dependents.join(", ") || "-"}</Text>
            {(task.task?.approach ?? []).length > 0 && (
              <Stack gap={2}>
                <Text fw={600}>Approach</Text>
                {(task.task?.approach ?? []).map((item, index) => (
                  <Text key={`${index}-${item}`} pl="md" size="sm">
                    - {item}
                  </Text>
                ))}
              </Stack>
            )}
            {task.plan ? (
              phases.map((phase, phaseIndex) => (
                <Stack gap="xs" key={`${phaseIndex}-${phase.title}`}>
                  <Text
                    c={phase.deleted ? "dimmed" : undefined}
                    fw={600}
                    td={phase.deleted ? "line-through" : undefined}
                  >
                    Phase {phaseIndex + 1}: {phase.title}
                  </Text>
                  {(phase.steps ?? []).map((step, stepIndex) => (
                    <Stack gap={0} key={`${stepIndex}-${step.description}`}>
                      <Text
                        c={phase.deleted || step.deleted ? "dimmed" : undefined}
                        pl="xl"
                        td={
                          phase.deleted || step.deleted
                            ? "line-through"
                            : undefined
                        }
                      >
                        [{stepMarker(step.state)}] {step.description}
                      </Text>
                      {step.skip_reason && (
                        <Text c="dimmed" pl="md" size="sm">
                          - skipped: {step.skip_reason}
                        </Text>
                      )}
                    </Stack>
                  ))}
                  {(phase.log ?? []).map((item, logIndex) => {
                    const legacy = typeof item === "string";
                    const [key, value] = legacy
                      ? [undefined, item]
                      : Object.entries(item.value)[0];
                    const text = key ? `[${key}]: ${value}` : value;
                    return (
                      <Text
                        c="dimmed"
                        key={`${logIndex}-${text}`}
                        pl="md"
                        size="sm"
                        td={
                          !legacy && item.deleted ? "line-through" : undefined
                        }
                      >
                        - {text}
                      </Text>
                    );
                  })}
                </Stack>
              ))
            ) : (
              <Text c="dimmed">plan: -</Text>
            )}
          </Stack>
        ) : null}
      </Box>
    </WidgetFrame>
  );
}
