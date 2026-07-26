import { MantineProvider } from "@mantine/core";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, useLocation } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { TasksPage } from "./TasksPage";

// cytoscapeの描画は本testの対象外なので、ノード選択だけを残して差し替える
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

function body(url: string): unknown {
  if (url.startsWith("/api/projects")) {
    return { projects: ["whub-dev"] };
  }
  if (url.startsWith("/api/tasks")) {
    return {
      tasks: [
        {
          id: "TASK-031",
          path: "a.yaml",
          title: "横断リスト",
          state: "in_progress",
          ready: false,
          depends_on: [],
        },
      ],
    };
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

describe("TasksPage", () => {
  it("依存グラフのノード選択で個別のTask詳細へ遷移する", async () => {
    render(
      <MantineProvider env="test">
        <MemoryRouter>
          <TasksPage />
          <LocationProbe />
        </MemoryRouter>
      </MantineProvider>,
    );

    fireEvent.click(
      await screen.findByRole("button", { name: "グラフのノード TASK-031" }),
    );

    expect(screen.getByTestId("location").textContent).toBe(
      "/tasks/whub-dev/TASK-031",
    );
  });
});
