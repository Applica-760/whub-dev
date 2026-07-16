import { requestJson } from '../../api/client';
import type { TaskResponse, TasksResponse } from '../../api/client';

export async function listTasks(): Promise<TasksResponse> {
  return requestJson<TasksResponse>('/api/tasks');
}

export async function getTask(taskId: string): Promise<TaskResponse> {
  return requestJson<TaskResponse>(`/api/tasks/${encodeURIComponent(taskId)}`);
}
