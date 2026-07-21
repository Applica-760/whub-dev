import { Stack } from "@mantine/core";

import { PageFrame } from "../../components/PageFrame";
import { ProjectAside } from "../projects/ProjectAside";
import { useProjectSelection } from "../projects/useProjectSelection";
import { KnowledgeWidget } from "./KnowledgeWidget";

export function KnowledgePage() {
  const projectSelection = useProjectSelection();

  return (
    <PageFrame aside={<ProjectAside {...projectSelection} />}>
      <Stack gap="md">
        <KnowledgeWidget project={projectSelection.selectedProject} />
      </Stack>
    </PageFrame>
  );
}
