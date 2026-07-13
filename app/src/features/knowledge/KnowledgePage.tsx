import {
  Alert,
  Stack,
  Text,
} from '@mantine/core';
import { useEffect, useState } from 'react';

import { GroupedListRow, GroupedListSection } from '../../components/GroupedList';
import { PageFrame } from '../../components/PageFrame';
import { useProjects } from '../projects/useProjects';
import { KnowledgeWidget } from './KnowledgeWidget';

export function KnowledgePage() {
  const { projects, loading: projectsLoading, error: projectsError } = useProjects();
  const [selectedProject, setSelectedProject] = useState<string | null>(null);

  useEffect(() => {
    setSelectedProject((current) => {
      if (current && projects.includes(current)) {
        return current;
      }
      return projects.includes('workspace-hub')
        ? 'workspace-hub'
        : (projects[0] ?? null);
    });
  }, [projects]);

  return (
    <PageFrame
      aside={
        <div className="page-aside-list">
          <GroupedListSection title="Project">
            {projectsLoading ? (
              <Text c="dimmed" p="md">Projectを読み込んでいます…</Text>
            ) : projects.length === 0 ? (
              <Text c="dimmed" p="md">Projectがありません</Text>
            ) : (
              projects.map((project) => (
                <GroupedListRow
                  key={project}
                  onClick={() => setSelectedProject(project)}
                  rightSection={project === selectedProject ? <Text c="blue" size="sm">選択中</Text> : undefined}
                  selected={project === selectedProject}
                  title={project}
                />
              ))
            )}
          </GroupedListSection>
        </div>
      }
    >
      <Stack gap="md">
        {projectsError && <Alert color="red" title="Projectを取得できませんでした">{projectsError}</Alert>}
        <KnowledgeWidget project={selectedProject} />
      </Stack>
    </PageFrame>
  );
}
