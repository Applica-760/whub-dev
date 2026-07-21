import { useEffect, useState } from "react";

import { useProjects } from "./useProjects";

export const DEFAULT_PROJECT = "workspace-hub";

export function useProjectSelection() {
  const projectState = useProjects();
  const [selectedProject, setSelectedProject] = useState<string | null>(null);

  useEffect(() => {
    setSelectedProject((current) => {
      if (current && projectState.projects.includes(current)) {
        return current;
      }
      return projectState.projects.includes(DEFAULT_PROJECT)
        ? DEFAULT_PROJECT
        : null;
    });
  }, [projectState.projects]);

  return {
    ...projectState,
    selectedProject,
    selectProject: setSelectedProject,
  };
}
