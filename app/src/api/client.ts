import type { paths } from "./generated/schema";

export type TodosResponse =
  paths["/api/todos"]["get"]["responses"][200]["content"]["application/json"];
export type ProjectsResponse =
  paths["/api/projects"]["get"]["responses"][200]["content"]["application/json"];
export type BacklogResponse =
  paths["/api/backlog/{project}"]["get"]["responses"][200]["content"]["application/json"];
export type KnowledgeResponse =
  paths["/api/knowledge/{project}"]["get"]["responses"][200]["content"]["application/json"];
export type VaultTreeResponse =
  paths["/api/vault/tree"]["get"]["responses"][200]["content"]["application/json"];
export type VaultNoteResponse =
  paths["/api/vault/note"]["get"]["responses"][200]["content"]["application/json"];
export type TasksResponse =
  paths["/api/tasks"]["get"]["responses"][200]["content"]["application/json"];
export type TaskResponse =
  paths["/api/tasks/{task_id}"]["get"]["responses"][200]["content"]["application/json"];
export type TaskGraphResponse =
  paths["/api/tasks/{task_id}/graph"]["get"]["responses"][200]["content"]["application/json"];
export type VaultNode = VaultTreeResponse["nodes"][number];

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function requestJson<T>(
  input: RequestInfo | URL,
  init?: RequestInit,
): Promise<T> {
  const response = await fetch(input, init);
  const data: unknown = await response.json().catch(() => undefined);

  if (!response.ok) {
    const message = detailFrom(data) ?? response.statusText;
    throw new ApiError(response.status, message);
  }

  return data as T;
}

function detailFrom(data: unknown): string | undefined {
  if (
    typeof data === "object" &&
    data !== null &&
    "detail" in data &&
    typeof data.detail === "string"
  ) {
    return data.detail;
  }
  return undefined;
}
