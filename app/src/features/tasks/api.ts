import { requestJson } from "../../api/client";
import type {
  AllTasksResponse,
  TaskResponse,
  TasksResponse,
} from "../../api/client";

function withProject(path: string, project?: string | null): string {
  return project ? `${path}?project=${encodeURIComponent(project)}` : path;
}

export async function listTasks(
  project?: string | null,
  active = false,
): Promise<TasksResponse> {
  return requestJson<TasksResponse>(
    withProject(active ? "/api/tasks/active" : "/api/tasks", project),
  );
}

export async function listAllActiveTasks(): Promise<AllTasksResponse> {
  return requestJson<AllTasksResponse>("/api/tasks/active/all");
}

export async function getTask(
  taskId: string,
  project?: string | null,
  active = false,
): Promise<TaskResponse> {
  return requestJson<TaskResponse>(
    withProject(
      `${active ? "/api/tasks/active" : "/api/tasks"}/${encodeURIComponent(taskId)}`,
      project,
    ),
  );
}
