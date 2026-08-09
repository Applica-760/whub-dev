import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { TaskDetailWidget } from "./TaskDetailWidget";

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

function renderWidget(node: React.ReactNode) {
  return render(<MantineProvider env="test">{node}</MantineProvider>);
}

describe("TaskDetailWidget", () => {
  it("Taskを指定するとTaskと依存元を表示する", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        response({
          path: "task-012.yaml",
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
          ],
        }),
      );
    vi.stubGlobal("fetch", fetchMock);

    renderWidget(<TaskDetailWidget project="local" taskId="TASK-012" />);

    expect(await screen.findByText("Project: local")).toBeTruthy();
    expect(screen.getByText("Task ID: TASK-012")).toBeTruthy();
    expect(screen.getByText("Depends on: TASK-010")).toBeTruthy();
    expect(screen.getByText("Depended on by: TASK-019")).toBeTruthy();
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

  it("Task未選択ではAPIを呼ばず選択案内を表示する", () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    renderWidget(<TaskDetailWidget project="local" taskId={null} />);

    expect(screen.getByText("Taskを選択してください")).toBeTruthy();
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
