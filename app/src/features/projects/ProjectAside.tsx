import { Text } from '@mantine/core';

import { GroupedListRow, GroupedListSection } from '../../components/GroupedList';

type ProjectAsideProps = {
  projects: string[];
  selectedProject: string | null;
  loading: boolean;
  error: string | null;
  selectProject: (project: string) => void;
};

export function ProjectAside({
  projects,
  selectedProject,
  loading,
  error,
  selectProject,
}: ProjectAsideProps) {
  return (
    <div className="page-aside-list">
      <GroupedListSection title="Project">
        {error ? (
          <Text c="red" p="md">Projectを取得できませんでした: {error}</Text>
        ) : loading ? (
          <Text c="dimmed" p="md">Projectを読み込んでいます…</Text>
        ) : projects.length === 0 ? (
          <Text c="dimmed" p="md">Projectがありません</Text>
        ) : (
          projects.map((project) => (
            <GroupedListRow
              key={project}
              onClick={() => selectProject(project)}
              rightSection={
                project === selectedProject
                  ? <Text c="blue" size="sm">選択中</Text>
                  : undefined
              }
              selected={project === selectedProject}
              title={project}
            />
          ))
        )}
      </GroupedListSection>
    </div>
  );
}
