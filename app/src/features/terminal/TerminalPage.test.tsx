import { MantineProvider } from "@mantine/core";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
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
          {
            parent_project: "vault",
            task_id: "TASK-101",
            branch: "tasks/101",
            workspace_path: "projects/worktrees/vault-101",
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
  it("左列の縦型UIでworktreeを選択し、中央と右列を表示する", async () => {
    const { container } = render(
      <MantineProvider env="test">
        <TerminalPage collapsed={{ left: false, right: false }} />
      </MantineProvider>,
    );

    const firstTerminal = await screen.findByRole("button", {
      name: /whub-dev.*TASK-099/,
    });
    const secondTerminal = screen.getByRole("button", {
      name: /vault.*TASK-101/,
    });
    await waitFor(() =>
      expect(firstTerminal.getAttribute("aria-pressed")).toBe("true"),
    );
    expect(screen.getByText("whub-dev / TASK-099")).toBeTruthy();

    fireEvent.click(secondTerminal);

    expect(firstTerminal.getAttribute("aria-pressed")).toBe("false");
    expect(secondTerminal.getAttribute("aria-pressed")).toBe("true");
    expect(screen.getByText("vault / TASK-101")).toBeTruthy();
    expect(
      screen.getByText("Session情報は後続のPhaseで追加します。"),
    ).toBeTruthy();
    expect(
      screen.getByText("Activity情報は後続のPhaseで追加します。"),
    ).toBeTruthy();
    expect(container.querySelectorAll(".overview-column")).toHaveLength(3);
    expect(container.querySelector(".terminal-frame")).toBeTruthy();
  });

  it("左右列へ折りたたみ状態を反映する", async () => {
    const { container } = render(
      <MantineProvider env="test">
        <TerminalPage collapsed={{ left: true, right: true }} />
      </MantineProvider>,
    );

    await screen.findByText("whub-dev / TASK-099");

    expect(
      container
        .querySelector('[data-side="left"]')
        ?.getAttribute("data-collapsed"),
    ).toBe("true");
    expect(
      container
        .querySelector('[data-side="right"]')
        ?.getAttribute("data-collapsed"),
    ).toBe("true");
    expect(
      container
        .querySelector(".overview-frame")
        ?.getAttribute("data-collapse-left"),
    ).toBe("true");
    expect(
      container
        .querySelector(".overview-frame")
        ?.getAttribute("data-collapse-right"),
    ).toBe("true");
  });
});
