import { requestJson } from '../../api/client';
import type { ProjectsResponse } from '../../api/client';

export async function listProjects(): Promise<string[]> {
  const response = await requestJson<ProjectsResponse>('/api/projects');
  return response.projects;
}
