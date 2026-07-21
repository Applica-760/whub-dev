import { Alert, Box, Tabs, Text } from "@mantine/core";

import { WidgetFrame } from "../../components/WidgetFrame";

type ProjectTabsWidgetProps = {
  projects: string[];
  selectedProject: string | null;
  loading: boolean;
  error: string | null;
  selectProject: (project: string) => void;
};

export function ProjectTabsWidget({
  projects,
  selectedProject,
  loading,
  error,
  selectProject,
}: ProjectTabsWidgetProps) {
  return (
    <WidgetFrame>
      <Box px="md" py="xs">
        {error ? (
          <Alert color="red" title="Projectを取得できませんでした">
            {error}
          </Alert>
        ) : loading ? (
          <Text c="dimmed">Projectを読み込んでいます…</Text>
        ) : projects.length === 0 ? (
          <Text c="dimmed">Projectがありません</Text>
        ) : (
          <Box style={{ overflowX: "auto" }}>
            <Tabs
              onChange={(project) => {
                if (project) {
                  selectProject(project);
                }
              }}
              value={selectedProject}
            >
              <Tabs.List
                aria-label="Projectを選択"
                style={{ flexWrap: "nowrap", minWidth: "max-content" }}
              >
                {projects.map((project) => (
                  <Tabs.Tab
                    key={project}
                    style={{ flexShrink: 0 }}
                    value={project}
                  >
                    {project}
                  </Tabs.Tab>
                ))}
              </Tabs.List>
            </Tabs>
          </Box>
        )}
      </Box>
    </WidgetFrame>
  );
}
