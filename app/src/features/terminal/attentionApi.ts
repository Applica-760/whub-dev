import { requestJson } from "../../api/client";
import type { paths } from "../../api/generated/schema";

export type ApprovalAttentionListResponse =
  paths["/api/agent-attention"]["get"]["responses"][200]["content"]["application/json"];
export type ApprovalAttention =
  ApprovalAttentionListResponse["attention"][number];

export async function listApprovalAttention(): Promise<ApprovalAttentionListResponse> {
  return requestJson<ApprovalAttentionListResponse>("/api/agent-attention");
}

export async function acknowledgeApprovalAttention(
  project: string,
  taskId: string,
): Promise<ApprovalAttention | null> {
  return requestJson<ApprovalAttention | null>(
    `/api/agent-attention/${encodeURIComponent(project)}/${encodeURIComponent(taskId)}/acknowledge`,
    { method: "POST" },
  );
}
