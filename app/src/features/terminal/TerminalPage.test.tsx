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
    label,
    project,
    taskId,
  }: {
    label?: string;
    project: string;
    taskId: string;
  }) => <div>{label ?? `${project} / ${taskId}`}</div>,
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
    vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/api/operator-terminal")
        return Promise.resolve({
          ok: true,
          json: async () =>
            init?.method === "POST"
              ? { state: "on", operator_id: "operator-1" }
              : { state: "off", operator_id: null },
        });
      if (url.includes("/changes"))
        return Promise.resolve({
          ok: true,
          json: async () => ({
            files: [{ path: "src/main.py", status: "M", previous_path: null }],
          }),
        });
      if (url.includes("/diff?"))
        return Promise.resolve({
          ok: true,
          json: async () => ({
            path: "src/main.py",
            content: "@@ -1 +1 @@\n-old\n+new",
          }),
        });
      return Promise.resolve({
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
      });
    }),
  );
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

function renderPage() {
  return render(
    <MantineProvider env="test">
      <TerminalPage />
    </MantineProvider>,
  );
}

describe("TerminalPage", () => {
  it("端末選択と差分を二段の1:2レイアウトで表示する", async () => {
    const { container } = renderPage();
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
    expect(await screen.findByText("src")).toBeTruthy();
    expect(await screen.findByText("new")).toBeTruthy();
    expect(
      container.querySelector(".diff-addition .diff-line-prefix")?.textContent,
    ).toBe("+");
    expect(container.querySelectorAll(".terminal-layout")).toHaveLength(1);
    expect(container.querySelectorAll(".terminal-diff-layout")).toHaveLength(1);

    fireEvent.click(secondTerminal);

    expect(firstTerminal.getAttribute("aria-pressed")).toBe("false");
    expect(secondTerminal.getAttribute("aria-pressed")).toBe("true");
    expect(screen.getByText("vault / TASK-101")).toBeTruthy();
    expect(fetch).toHaveBeenCalledWith(
      "/api/worktrees/vault/TASK-101/changes",
      undefined,
    );
  });

  it("Operatorトグルで専用terminalを選択する", async () => {
    renderPage();
    fireEvent.click(
      await screen.findByRole("switch", { name: "Operatorを開始" }),
    );
    expect(await screen.findByText("Operator / workspace-hub")).toBeTruthy();
    expect(
      (
        screen.getByRole("switch", {
          name: "Operatorを停止",
        }) as HTMLInputElement
      ).checked,
    ).toBe(true);
  });
});
