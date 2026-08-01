import { MantineProvider } from "@mantine/core";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { TerminalPage } from "./TerminalPage";

vi.mock("./TerminalWidget", () => ({
  TerminalWidget: ({
    project,
    taskId,
  }: {
    project: string;
    taskId: string;
  }) => <div>{`${project} / ${taskId}`}</div>,
}));

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
    vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        worktrees: [
          {
            parent_project: "whub-dev",
            task_id: "TASK-099",
            branch: "tasks/099",
            workspace_path: "projects/worktrees/whub-dev-099",
            diagnostics: [],
          },
        ],
      }),
    }),
  );
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("TerminalPage", () => {
  it("worktreeを初期選択し、上段と3列の骨格を表示する", async () => {
    const { container } = render(
      <MantineProvider env="test">
        <TerminalPage />
      </MantineProvider>,
    );

    expect(await screen.findByDisplayValue("whub-dev / TASK-099")).toBeTruthy();
    expect(screen.getAllByText("whub-dev / TASK-099")).toHaveLength(2);
    expect(
      screen.getByText("Session情報は後続のPhaseで追加します。"),
    ).toBeTruthy();
    expect(
      screen.getByText("Activity情報は後続のPhaseで追加します。"),
    ).toBeTruthy();
    expect(container.querySelectorAll(".overview-column")).toHaveLength(3);
  });
});
