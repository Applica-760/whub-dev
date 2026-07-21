import { requestJson } from "../../api/client";
import type {
  TaskGraphResponse,
  TaskResponse,
  TasksResponse,
} from "../../api/client";

function withProject(path: string, project?: string | null): string {
  return project ? `${path}?project=${encodeURIComponent(project)}` : path;
}

export async function listTasks(
  project?: string | null,
): Promise<TasksResponse> {
  return requestJson<TasksResponse>(withProject("/api/tasks", project));
}

export async function getTask(
  taskId: string,
  project?: string | null,
): Promise<TaskResponse> {
  return requestJson<TaskResponse>(
    withProject(`/api/tasks/${encodeURIComponent(taskId)}`, project),
  );
}

export async function getTaskFlowGraph(
  taskId: string,
  project?: string | null,
): Promise<TaskGraphResponse> {
  return requestJson<TaskGraphResponse>(
    withProject(`/api/tasks/${encodeURIComponent(taskId)}/graph`, project),
  );
}
