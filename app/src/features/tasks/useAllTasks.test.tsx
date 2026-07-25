import { renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { useAllTasks } from "./useAllTasks";

afterEach(() => {
  vi.unstubAllGlobals();
});

function response(body: unknown): Response {
  return {
    ok: true,
    json: async () => body,
  } as Response;
}

describe("useAllTasks", () => {
  it("全ProjectのTaskをproject付きで平坦化し、失敗Projectはerrorとして保持する", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      response({
        projects: [
          {
            project: "whub-dev",
            tasks: [{ id: "TASK-031", path: "a.yaml", depends_on: [] }],
            error: null,
          },
          {
            project: "vault",
            tasks: [{ id: "TASK-001", path: "b.yaml", depends_on: [] }],
            error: null,
          },
          { project: "private", tasks: [], error: "project resource is not available" },
        ],
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const { result } = renderHook(() => useAllTasks());

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(fetchMock).toHaveBeenCalledWith("/api/tasks/all", undefined);
    expect(result.current.tasks).toEqual([
      { id: "TASK-031", path: "a.yaml", depends_on: [], project: "whub-dev" },
      { id: "TASK-001", path: "b.yaml", depends_on: [], project: "vault" },
    ]);
    expect(result.current.projectErrors).toEqual([
      { project: "private", error: "project resource is not available" },
    ]);
    expect(result.current.error).toBeNull();
  });
});
