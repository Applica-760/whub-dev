import { Alert, Anchor, Badge, Box, Stack, Text } from "@mantine/core";
import { useMemo } from "react";
import { NavLink } from "react-router";

import { GroupedListRow } from "../../components/GroupedList";
import { WidgetFrame } from "../../components/WidgetFrame";
import { stateColor } from "./taskState";
import type { ProjectTaskSummary } from "./useAllTasks";
import { useAllTasks } from "./useAllTasks";

export type SelectedTask = { project: string; taskId: string };

type AllTasksWidgetProps = {
  selectedTask?: SelectedTask | null;
  onSelectTask: (project: string, taskId: string) => void;
  showAllLink?: boolean;
};

type IdentifiedTask = ProjectTaskSummary & { id: string };

type TaskGroup = { project: string; tasks: IdentifiedTask[] };

function groupByProject(tasks: IdentifiedTask[]): TaskGroup[] {
  const groups: TaskGroup[] = [];
  tasks.forEach((task) => {
    const group = groups.find((item) => item.project === task.project);
    if (group) {
      group.tasks.push(task);
      return;
    }
    groups.push({ project: task.project, tasks: [task] });
  });
  return groups;
}

export function AllTasksWidget({
  selectedTask,
  onSelectTask,
  showAllLink = false,
}: AllTasksWidgetProps) {
  const { tasks, projectErrors, loading, error } = useAllTasks();
  const groups = useMemo(
    () =>
      groupByProject(
        tasks.filter(
          (task): task is IdentifiedTask =>
            Boolean(task.id) && (task.ready || task.state === "in_progress"),
        ),
      ),
    [tasks],
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
          Task (all projects)
        </Text>
      }
    >
      {error ? (
        <Box p="md">
          <Alert color="red" title="Taskを取得できませんでした">
            {error}
          </Alert>
        </Box>
      ) : loading ? (
        <Box p="md">
          <Text c="dimmed">Taskを読み込んでいます…</Text>
        </Box>
      ) : (
        <Stack gap="md" py="xs">
          {/* Project単位の失敗は警告に留め、取得できたProjectの行は描画し続ける */}
          {projectErrors.length > 0 && (
            <Box px="md">
              <Alert color="yellow" title="一部Projectを取得できませんでした">
                <Stack gap={2}>
                  {projectErrors.map((projectError) => (
                    <Text key={projectError.project} size="sm">
                      {projectError.project}: {projectError.error}
                    </Text>
                  ))}
                </Stack>
              </Alert>
            </Box>
          )}
          {groups.length === 0 ? (
            <Text c="dimmed" px="md">
              着手中・着手可能なTaskはありません
            </Text>
          ) : (
            groups.map((group) => (
              <Stack gap={4} key={group.project}>
                <Text c="dimmed" fw={600} px="md" size="sm">
                  {group.project}
                </Text>
                {group.tasks.map((task, index) => (
                  <GroupedListRow
                    key={`${task.project}/${task.id}`}
                    onClick={() => onSelectTask(task.project, task.id)}
                    rightSection={
                      <Badge
                        color={stateColor(task.state)}
                        size="sm"
                        variant="light"
                      >
                        {task.state ?? "invalid"}
                      </Badge>
                    }
                    selected={
                      selectedTask?.project === task.project &&
                      selectedTask?.taskId === task.id
                    }
                    title={
                      task.title
                        ? `${task.id.replace(/^TASK-/, "")}: ${task.title}`
                        : task.id.replace(/^TASK-/, "")
                    }
                    withDivider={index < group.tasks.length - 1}
                  />
                ))}
              </Stack>
            ))
          )}
        </Stack>
      )}
    </WidgetFrame>
  );
}
