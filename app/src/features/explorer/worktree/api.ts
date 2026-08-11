import { requestJson } from "../../../api/client";
import type { paths } from "../../../api/generated/schema";

type ChangedFilesResponse =
  paths["/api/worktrees/{project}/{task_id}/changes"]["get"]["responses"][200]["content"]["application/json"];
type WorktreeDiffResponse =
  paths["/api/worktrees/{project}/{task_id}/diff"]["get"]["responses"][200]["content"]["application/json"];

export type ChangedFile = ChangedFilesResponse["files"][number];
export type WorktreeFile = WorktreeDiffResponse;

export async function fetchChangedFiles(project: string, taskId: string) {
  return requestJson<ChangedFilesResponse>(
    `/api/worktrees/${encodeURIComponent(project)}/${encodeURIComponent(taskId)}/changes`,
  );
}

export async function fetchWorktreeDiff(
  project: string,
  taskId: string,
  path: string,
) {
  return requestJson<WorktreeDiffResponse>(
    `/api/worktrees/${encodeURIComponent(project)}/${encodeURIComponent(taskId)}/diff?path=${encodeURIComponent(path)}`,
  );
}
