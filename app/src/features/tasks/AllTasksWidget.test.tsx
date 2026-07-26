import { MantineProvider } from "@mantine/core";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AllTasksWidget } from "./AllTasksWidget";

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
  // globals未有効でRTLの自動cleanupが登録されないため、明示的に前のDOMを破棄する
  cleanup();
  vi.unstubAllGlobals();
});

function response(body: unknown): Response {
  return {
    ok: true,
    json: async () => body,
  } as Response;
}

function stubTasks(projects: unknown[]) {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response({ projects })));
}

function renderWidget(node: React.ReactNode) {
  return render(
    <MantineProvider env="test">
      <MemoryRouter>{node}</MemoryRouter>
    </MantineProvider>,
  );
}

describe("AllTasksWidget", () => {
  it("readyまたはin_progressのTaskだけをProject別に並べる", async () => {
    stubTasks([
      {
        project: "whub-dev",
        error: null,
        tasks: [
          {
            id: "TASK-031",
            path: "a.yaml",
            title: "横断リスト",
            state: "in_progress",
            ready: false,
          },
          {
            id: "TASK-040",
            path: "b.yaml",
            title: "完了済み",
            state: "completed",
            ready: false,
          },
        ],
      },
      {
        project: "vault",
        error: null,
        tasks: [
          {
            id: "TASK-001",
            path: "c.yaml",
            title: "整理",
            state: "draft",
            ready: true,
          },
        ],
      },
    ]);

    renderWidget(<AllTasksWidget onSelectTask={vi.fn()} />);

    expect(await screen.findByText("031: 横断リスト")).toBeTruthy();
    expect(screen.getByText("001: 整理")).toBeTruthy();
    expect(screen.queryByText("040: 完了済み")).toBeNull();
    expect(screen.getByText("whub-dev")).toBeTruthy();
    expect(screen.getByText("vault")).toBeTruthy();
  });

  it("区切り線をProject間だけに置き、同一Project内のTask間には置かない", async () => {
    stubTasks([
      {
        project: "whub-dev",
        error: null,
        tasks: [
          { id: "TASK-031", path: "a.yaml", title: "A", state: "in_progress" },
          { id: "TASK-032", path: "b.yaml", title: "B", ready: true },
        ],
      },
      {
        project: "vault",
        error: null,
        tasks: [
          { id: "TASK-001", path: "c.yaml", title: "C", ready: true },
          { id: "TASK-002", path: "d.yaml", title: "D", ready: true },
        ],
      },
    ]);

    const { container } = renderWidget(<AllTasksWidget onSelectTask={vi.fn()} />);

    expect(await screen.findByText("031: A")).toBeTruthy();
    // 2 Project・計4 Taskで、区切り線はProject境界の1本だけになる
    expect(container.querySelectorAll(".mantine-Divider-root")).toHaveLength(1);
  });

  it("行を選択すると(project, taskId)を通知し、選択中の行を区別する", async () => {
    stubTasks([
      {
        project: "vault",
        error: null,
        tasks: [
          {
            id: "TASK-001",
            path: "c.yaml",
            title: "整理",
            state: "draft",
            ready: true,
          },
        ],
      },
    ]);
    const onSelectTask = vi.fn();

    renderWidget(
      <AllTasksWidget
        onSelectTask={onSelectTask}
        selectedTask={{ project: "vault", taskId: "TASK-001" }}
      />,
    );

    const row = await screen.findByRole("button", { name: /001: 整理/ });
    expect(row.getAttribute("aria-pressed")).toBe("true");

    fireEvent.click(row);

    expect(onSelectTask).toHaveBeenCalledWith("vault", "TASK-001");
  });

  it("取得失敗Projectを警告として示し、他Projectの行は描画し続ける", async () => {
    stubTasks([
      {
        project: "whub-dev",
        error: null,
        tasks: [
          {
            id: "TASK-031",
            path: "a.yaml",
            title: "横断リスト",
            state: "in_progress",
            ready: false,
          },
        ],
      },
      { project: "private", error: "project resource is not available", tasks: [] },
    ]);

    renderWidget(<AllTasksWidget onSelectTask={vi.fn()} />);

    expect(await screen.findByText("031: 横断リスト")).toBeTruthy();
    expect(screen.getByText("一部Projectを取得できませんでした")).toBeTruthy();
    expect(
      screen.getByText("private: project resource is not available"),
    ).toBeTruthy();
  });
});
