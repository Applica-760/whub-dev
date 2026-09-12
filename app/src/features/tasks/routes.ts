export const TASKS_PATH = "/tasks";

export function isTasksRoute(pathname: string): boolean {
  return pathname === TASKS_PATH;
}
