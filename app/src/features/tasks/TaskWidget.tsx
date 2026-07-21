import { Alert, Anchor, Badge, Box, Stack, Text } from "@mantine/core";
import { NavLink } from "react-router";

import { WidgetFrame } from "../../components/WidgetFrame";
import { taskDetailPath } from "./routes";
import { useTasks } from "./useTasks";

type TaskWidgetProps = {
  project: string | null;
  overviewOnly?: boolean;
  showAllLink?: boolean;
};

function stateColor(state: string | null | undefined): string {
  if (state === "completed") {
    return "green";
  }
  if (state === "in_progress") {
    return "blue";
  }
  return "gray";
}

function listStateOrder(state: string | null | undefined): number {
  return { in_progress: 0, draft: 1, completed: 2 }[state ?? ""] ?? 3;
}

export function TaskWidget({
  project,
  overviewOnly = false,
  showAllLink = false,
}: TaskWidgetProps) {
  const { tasks, loading, error } = useTasks(project);
  const visibleTasks = overviewOnly
    ? tasks.filter((task) => task.ready || task.state === "in_progress")
    : [...tasks].sort(
        (left, right) =>
          listStateOrder(left.state) - listStateOrder(right.state),
      );

  return (
    <WidgetFrame
      action={
        showAllLink ? (
          <Anchor component={NavLink} size="sm" to="/tasks">
            すべて表示
          </Anchor>
        ) : undefined
      }
      title={
        <Text c="dimmed" fw={600} size="sm">
          Task
        </Text>
      }
    >
      <Box p="md">
        {error ? (
          <Alert color="red" title="Taskを取得できませんでした">
            {error}
          </Alert>
        ) : loading ? (
          <Text c="dimmed">Taskを読み込んでいます…</Text>
        ) : !project ? (
          <Text c="dimmed">表示するProjectを選択してください</Text>
        ) : visibleTasks.length === 0 ? (
          <Text c="dimmed">
            {overviewOnly
              ? "着手中・着手可能なTaskはありません"
              : "Taskはありません"}
          </Text>
        ) : (
          <Stack gap="sm">
            {visibleTasks.map((task) => (
              <Stack gap={2} key={task.path}>
                {task.id ? (
                  <Anchor
                    component={NavLink}
                    fw={500}
                    to={taskDetailPath(project, task.id)}
                  >
                    {task.title
                      ? `${task.id.replace(/^TASK-/, "")}: ${task.title}`
                      : task.id.replace(/^TASK-/, "")}
                  </Anchor>
                ) : (
                  <Text fw={500}>{task.path}</Text>
                )}
                <Badge
                  color={stateColor(task.state)}
                  size="sm"
                  variant="light"
                  w="fit-content"
                >
                  {task.state ?? "invalid"}
                </Badge>
                {(task.blocked_by ?? []).map((reason) => (
                  <Text c="dimmed" key={reason} size="sm">
                    {reason}
                  </Text>
                ))}
                {(task.diagnostics ?? []).map((diagnostic) => (
                  <Text c="red" key={diagnostic} size="sm">
                    {diagnostic}
                  </Text>
                ))}
              </Stack>
            ))}
          </Stack>
        )}
      </Box>
    </WidgetFrame>
  );
}
