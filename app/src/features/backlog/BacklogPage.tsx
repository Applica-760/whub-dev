import { Stack } from '@mantine/core';

import { PageFrame } from '../../components/PageFrame';
import { ProjectAside } from '../projects/ProjectAside';
import { useProjectSelection } from '../projects/useProjectSelection';
import { BacklogWidget } from './BacklogWidget';

export function BacklogPage() {
  const projectSelection = useProjectSelection();

  return (
    <PageFrame
      aside={<ProjectAside {...projectSelection} />}
    >
      <Stack gap="md">
        <BacklogWidget project={projectSelection.selectedProject} />
      </Stack>
    </PageFrame>
  );
}
