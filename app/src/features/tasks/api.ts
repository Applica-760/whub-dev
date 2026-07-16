import { requestJson } from '../../api/client';
import type { TaskGraphResponse, TaskResponse, TasksResponse } from '../../api/client';

export async function listTasks(): Promise<TasksResponse> {
  return requestJson<TasksResponse>('/api/tasks');
}

export async function getTask(taskId: string): Promise<TaskResponse> {
  return requestJson<TaskResponse>(`/api/tasks/${encodeURIComponent(taskId)}`);
}

export async function getTaskDependencyGraph(): Promise<TaskGraphResponse> {
  return requestJson<TaskGraphResponse>('/api/tasks/graph');
}

export async function getTaskFlowGraph(taskId: string): Promise<TaskGraphResponse> {
  return requestJson<TaskGraphResponse>(`/api/tasks/${encodeURIComponent(taskId)}/graph`);
}
