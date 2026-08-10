import { MantineProvider } from "@mantine/core";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, useLocation } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { OverviewPage } from "./OverviewPage";

// cytoscape・mermaidの描画は本testの対象外なので、選択操作だけを残して差し替える
vi.mock("../../components/TaskDependencyGraph", () => ({
  TaskDependencyGraph: ({
    tasks,
    onSelectTask,
  }: {
    tasks: { id?: string | null }[];
    onSelectTask?: (taskId: string) => void;
  }) =>
    tasks.map((task) => (
      <button
        key={task.id}
        onClick={() => onSelectTask?.(task.id ?? "")}
        type="button"
      >
        グラフのノード {task.id}
      </button>
    )),
}));

const TASKS_BY_PROJECT: Record<string, unknown[]> = {
  "whub-dev": [
    {
      id: "TASK-031",
      path: "a.yaml",
      title: "横断リスト",
      state: "in_progress",
      ready: false,
      depends_on: [],
    },
  ],
  vault: [
    {
      id: "TASK-001",
      path: "b.yaml",
      title: "整理",
      state: "draft",
      ready: true,
      depends_on: [],
    },
  ],
};

function taskDetail(taskId: string) {
  return {
    schema_version: 1,
    task: {
      id: taskId,
      state: "in_progress",
      title: `${taskId}の詳細`,
      objective: "",
      approach: [],
      depends_on: [],
      interruption_task_id: null,
      interruption_reason: null,
      interruption_source_task_id: null,
    },
    plan: null,
    approvals: [],
    acceptance_results: [],
    change_requests: [],
    cancellation: null,
    result: null,
  };
}

function body(url: string): unknown {
  if (url.startsWith("/api/todos")) {
    return { pending: [], completed: [] };
  }
  if (url.startsWith("/api/resources/status")) {
    return { resources: [] };
  }
  if (url.startsWith("/api/projects")) {
    return { projects: ["whub-dev", "vault"] };
  }
  if (url.startsWith("/api/backlog/")) {
    return {
      project: decodeURIComponent(url.slice("/api/backlog/".length)),
      content: "",
    };
  }
  if (url.startsWith("/api/tasks/all")) {
    return {
      projects: Object.entries(TASKS_BY_PROJECT).map(([project, tasks]) => ({
        project,
        tasks,
        error: null,
      })),
    };
  }
  if (url.startsWith("/api/tasks/")) {
    return taskDetail(
      decodeURIComponent(url.slice("/api/tasks/".length).split("?")[0]),
    );
  }
  if (url.startsWith("/api/tasks")) {
    const project = new URLSearchParams(url.split("?")[1] ?? "").get("project");
    return { tasks: TASKS_BY_PROJECT[project ?? ""] ?? [] };
  }
  throw new Error(`unexpected request: ${url}`);
}

beforeEach(() => {
  vi.stubGlobal(
    "matchMedia",
    vi.fn().mockReturnValue({
      matches: false,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    }),
  );
  // jsdomにResizeObserverが無く、MantineのScrollAreaが初期描画で落ちる
  vi.stubGlobal(
    "ResizeObserver",
    class {
      observe() {}
      unobserve() {}
      disconnect() {}
    },
  );
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: string) => ({
      ok: true,
      json: async () => body(input),
    })),
  );
});

afterEach(() => {
  // globals未有効でRTLの自動cleanupが登録されないため、明示的に前のDOMを破棄する
  cleanup();
  vi.unstubAllGlobals();
});

function LocationProbe() {
  return <div data-testid="location">{useLocation().pathname}</div>;
}

function renderOverview() {
  return render(
    <MantineProvider env="test">
      <MemoryRouter>
        <OverviewPage collapsed={{ left: false, right: false }} />
        <LocationProbe />
      </MemoryRouter>
    </MantineProvider>,
  );
}

describe("OverviewPage", () => {
  it("横断リストの選択でタスク確認Widgetへ切り替え、URL遷移しない", async () => {
    renderOverview();

    expect(
      screen.getByText("リストまたはグラフからTaskを選択してください"),
    ).toBeTruthy();

    fireEvent.click(await screen.findByRole("button", { name: /001: 整理/ }));

    expect(await screen.findByText("TASK-001(in_progress)")).toBeTruthy();
    expect(screen.getByTestId("location").textContent).toBe("/");
  });

  it("依存グラフのノード選択でもURL遷移せず表示Taskを切り替える", async () => {
    renderOverview();

    fireEvent.click(
      await screen.findByRole("button", { name: "グラフのノード TASK-031" }),
    );

    expect(await screen.findByText("TASK-031(in_progress)")).toBeTruthy();
    expect(screen.getByTestId("location").textContent).toBe("/");
  });

  it("Projectタブを切り替えても選択Taskは解除されない", async () => {
    renderOverview();

    // 選択後にタブを別Projectへ移し、依存グラフだけが切替先Projectへ追従することを見る
    fireEvent.click(
      await screen.findByRole("button", { name: /031: 横断リスト/ }),
    );
    expect(await screen.findByText("TASK-031(in_progress)")).toBeTruthy();

    fireEvent.click(await screen.findByRole("tab", { name: "vault" }));

    expect(await screen.findByText("TASK-031(in_progress)")).toBeTruthy();
    expect(vi.mocked(fetch)).toHaveBeenCalledWith(
      "/api/tasks?project=vault",
      undefined,
    );
  });
});
