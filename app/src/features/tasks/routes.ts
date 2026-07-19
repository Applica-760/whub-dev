export const TASKS_PATH = '/tasks';
export const TASK_DETAIL_PATH = `${TASKS_PATH}/:project/:taskId`;
export const LEGACY_TASK_DETAIL_PATH = `${TASKS_PATH}/:taskId`;

export function isTasksRoute(pathname: string): boolean {
  return pathname === TASKS_PATH || pathname.startsWith(`${TASKS_PATH}/`);
}

export function taskDetailPath(project: string, taskId: string): string {
  return `${TASKS_PATH}/${encodeURIComponent(project)}/${encodeURIComponent(taskId)}`;
}
