import { requestJson } from "../../api/client";
import type { paths } from "../../api/generated/schema";

export type WorktreeListResponse =
  paths["/api/worktrees"]["get"]["responses"][200]["content"]["application/json"];
export type WorktreeItem = WorktreeListResponse["worktrees"][number];

export async function listWorktrees(): Promise<WorktreeListResponse> {
  return requestJson<WorktreeListResponse>("/api/worktrees");
}
