import { Stack } from "@mantine/core";

import { PageFrame } from "../../components/PageFrame";
import { ProjectAside } from "../projects/ProjectAside";
import { useProjectSelection } from "../projects/useProjectSelection";
import { TaskDependencyGraphWidget } from "./TaskDependencyGraphWidget";
import { TaskWidget } from "./TaskWidget";

export function TasksPage() {
  const projectSelection = useProjectSelection();

  return (
    <PageFrame aside={<ProjectAside {...projectSelection} />}>
      <Stack gap="md">
        <TaskDependencyGraphWidget project={projectSelection.selectedProject} />
        <TaskWidget project={projectSelection.selectedProject} />
      </Stack>
    </PageFrame>
  );
}
