import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { TaskDetailPage } from "./TaskDetailPage";

beforeEach(() => {
  vi.stubGlobal(
    "matchMedia",
    vi.fn().mockReturnValue({
      matches: false,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    }),
  );
});

afterEach(() => {
  vi.unstubAllGlobals();
});

function response(body: unknown): Response {
  return {
    ok: true,
    json: async () => body,
  } as Response;
}

describe("TaskDetailPage", () => {
  it("Projectを指定してTaskと依存関係を表示する", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        response({
          path: "done/task-012.yaml",
          title: "開発モード",
          markdown: "# 開発モード\n\n確認を速くする",
          task: {
            schema_version: 2,
            id: "TASK-012",
            workflow: "WF-001",
            state: "in_progress",
            depends_on: ["TASK-010"],
          },
        }),
      )
      .mockResolvedValueOnce(
        response({
          tasks: [
            { depends_on: [], id: "TASK-010", path: "done/task-010.yaml" },
            { depends_on: ["TASK-012"], id: "TASK-019", path: "task-019.yaml" },
            { depends_on: ["TASK-012"], id: "TASK-020", path: "task-020.yaml" },
          ],
        }),
      );
    vi.stubGlobal("fetch", fetchMock);

    render(
      <MantineProvider env="test">
        <MemoryRouter initialEntries={["/tasks/local/TASK-012"]}>
          <Routes>
            <Route
              path="/tasks/:project/:taskId"
              element={<TaskDetailPage />}
            />
          </Routes>
        </MemoryRouter>
      </MantineProvider>,
    );

    expect(await screen.findByText("TASK-012(in_progress)")).toBeTruthy();
    expect(
      screen.getByText("(TASK-010) -> (TASK-012) -> (TASK-019, TASK-020)"),
    ).toBeTruthy();
    expect(screen.getByText("確認を速くする")).toBeTruthy();
    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "/api/tasks/TASK-012?project=local",
      undefined,
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      "/api/tasks?project=local",
      undefined,
    );
  });
});
