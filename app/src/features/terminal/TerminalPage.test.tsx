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

let approvalAttention = [
  {
    project: "vault",
    task_id: "TASK-101",
    tool_name: "Bash",
    requested_at: "2026-08-03T00:00:00+00:00",
    acknowledged: false,
  },
];
let agentError: string | null = null;
let operationStarts = 0;
let changedFiles = [{ path: "src/main.py", status: "M", previous_path: null }];
let clipboardWrite = vi.fn();

vi.mock("./TerminalWidget", () => ({
  TerminalWidget: ({
    label,
    project,
    taskId,
  }: {
    label?: string;
    project?: string;
    taskId?: string;
  }) => <div>{label ?? `${project} / ${taskId}`}</div>,
}));

beforeEach(() => {
  agentError = null;
  operationStarts = 0;
  changedFiles = [{ path: "src/main.py", status: "M", previous_path: null }];
  clipboardWrite = vi.fn();
  Object.defineProperty(navigator, "clipboard", {
    configurable: true,
    value: { writeText: clipboardWrite },
  });
  approvalAttention = [
    {
      project: "vault",
      task_id: "TASK-101",
      tool_name: "Bash",
      requested_at: "2026-08-03T00:00:00+00:00",
      acknowledged: false,
    },
  ];
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
    "confirm",
    vi.fn(() => true),
  );
  vi.stubGlobal(
    "fetch",
    vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/api/operator-terminals")
        return Promise.resolve({
          ok: true,
          json: async () =>
            init?.method === "POST"
              ? { operator_id: `operator-${++operationStarts}` }
              : { terminals: [] },
        });
      if (url === "/api/agent-attention")
        return Promise.resolve({
          ok: true,
          json: async () => ({
            attention: approvalAttention,
          }),
        });
      if (url.includes("/acknowledge"))
        return Promise.resolve({
          ok: true,
          json: async () => ({
            ...approvalAttention[0],
            acknowledged: true,
          }),
        });
      if (url.includes("/api/agent-codex/"))
        return Promise.resolve({
          ok: true,
          json: async () =>
            init?.method === "POST"
              ? undefined
              : {
                  active_turn_id: null,
                  messages: [],
                  approvals: [],
                  error: agentError,
                },
        });
      if (url.startsWith("/api/tasks/"))
        return Promise.resolve({
          ok: true,
          json: async () => ({
            schema_version: 1,
            task: {
              id: url.includes("TASK-101") ? "TASK-101" : "TASK-099",
              state: "in_progress",
              title: "Terminal task",
              approach: [],
              depends_on: [],
            },
            plan: { phases: [] },
          }),
        });
      if (url.startsWith("/api/tasks?"))
        return Promise.resolve({
          ok: true,
          json: async () => ({ tasks: [] }),
        });
      if (url.includes("/changes"))
        return Promise.resolve({
          ok: true,
          json: async () => ({
            files: changedFiles,
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
  it("Task詳細・端末・ExplorerとGit差分を表示する", async () => {
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
    expect(await screen.findByText("Task ID: TASK-099")).toBeTruthy();
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
    expect(screen.getAllByText("vault / TASK-101")).not.toHaveLength(0);
    expect(fetch).toHaveBeenCalledWith(
      "/api/worktrees/vault/TASK-101/changes",
      undefined,
    );
  });

  it("Git Explorerを初期折りたたみで表示し、状態と右クリックコピーを反映する", async () => {
    changedFiles = [
      { path: "src/main.py", status: "M", previous_path: null },
      { path: "draft.txt", status: "A", previous_path: null },
    ];
    const { container } = renderPage();

    const source = await screen.findByText("src");
    expect(
      container
        .querySelector(".diff-tree-chevron")
        ?.getAttribute("data-expanded"),
    ).toBeNull();
    expect(container.querySelector('[data-changed="true"]')).toBeTruthy();
    expect(container.querySelector('[data-new="true"]')).toBeTruthy();

    fireEvent.click(source);
    expect(await screen.findByText("main.py")).toBeTruthy();
    expect(
      container
        .querySelector(".diff-tree-chevron")
        ?.getAttribute("data-expanded"),
    ).toBe("true");
    fireEvent.contextMenu(screen.getByText("main.py"));
    expect(clipboardWrite).toHaveBeenCalledWith(
      "projects/worktrees/whub-dev-099/src/main.py",
    );
  });

  it("複数Operationを起動・選択・個別終了できる", async () => {
    renderPage();
    const start = await screen.findByRole("button", {
      name: "Operationを起動",
    });
    fireEvent.click(start);
    expect(await screen.findByText("Operation / workspace-hub")).toBeTruthy();

    fireEvent.click(start);
    expect(
      await screen.findByRole("switch", { name: "Operation operator-2を停止" }),
    ).toBeTruthy();
    fireEvent.click(
      screen.getByRole("switch", { name: "Operation operator-1を停止" }),
    );

    await waitFor(() =>
      expect(fetch).toHaveBeenCalledWith("/api/operator-terminals/operator-1", {
        method: "DELETE",
      }),
    );
    expect(
      screen.queryByRole("switch", { name: "Operation operator-1を停止" }),
    ).toBeNull();
  });

  it("承認待ちのTerminalをExplorerバッジと選択行で示す", async () => {
    renderPage();

    expect(await screen.findByText("承認待ち")).toBeTruthy();
    expect(screen.queryByText("承認待ちのTerminalがあります")).toBeNull();

    fireEvent.click(
      await screen.findByRole("button", { name: /vault.*TASK-101/ }),
    );

    expect(await screen.findByText("vault / TASK-101")).toBeTruthy();
    await waitFor(() =>
      expect(fetch).toHaveBeenCalledWith(
        "/api/agent-attention/vault/TASK-101/acknowledge",
        { method: "POST" },
      ),
    );
  });

  it("承認待ちをブラウザタブのタイトルとfaviconで示す", async () => {
    renderPage();

    await waitFor(() => expect(document.title).toBe("🔔 (1) whub"));
    const icon = document.head.querySelector<HTMLLinkElement>(
      'link[data-whub-attention-icon="true"]',
    );
    expect(icon?.href.endsWith("/attention-favicon.svg")).toBe(true);
  });

  it("既に選択済みのTerminalへ新着の承認待ちが来ても既読化しない", async () => {
    approvalAttention = [
      {
        project: "whub-dev",
        task_id: "TASK-099",
        tool_name: "Bash",
        requested_at: "2026-08-03T00:00:00+00:00",
        acknowledged: false,
      },
    ];

    renderPage();

    expect(await screen.findByText("承認待ち")).toBeTruthy();
    expect(fetch).not.toHaveBeenCalledWith(
      "/api/agent-attention/whub-dev/TASK-099/acknowledge",
      { method: "POST" },
    );
  });

  it("明示的に選択したTerminalの承認待ちだけを既読化する", async () => {
    approvalAttention = [
      {
        project: "whub-dev",
        task_id: "TASK-099",
        tool_name: "Bash",
        requested_at: "2026-08-03T00:00:00+00:00",
        acknowledged: false,
      },
    ];
    renderPage();

    fireEvent.click(
      await screen.findByRole("button", { name: /whub-dev.*TASK-099/ }),
    );

    await waitFor(() =>
      expect(fetch).toHaveBeenCalledWith(
        "/api/agent-attention/whub-dev/TASK-099/acknowledge",
        { method: "POST" },
      ),
    );
  });

  it("TerminalとAgentを右ペインで切り替える", async () => {
    renderPage();

    const terminal = await screen.findByRole("button", { name: "Terminal" });
    const agent = screen.getByRole("button", { name: "Agent" });
    expect(terminal.getAttribute("aria-pressed")).toBe("true");
    expect(agent.getAttribute("aria-pressed")).toBe("false");
    expect(screen.queryByPlaceholderText("Codexへ依頼…")).toBeNull();
    await waitFor(() => expect(agent.getAttribute("disabled")).toBeNull());

    fireEvent.click(agent);

    await waitFor(() =>
      expect(agent.getAttribute("aria-pressed")).toBe("true"),
    );
    expect(await screen.findByPlaceholderText("Codexへ依頼…")).toBeTruthy();
  });

  it("Codex promptをJSONとして送信する", async () => {
    renderPage();

    const agent = await screen.findByRole("button", { name: "Agent" });
    await waitFor(() => expect(agent.getAttribute("disabled")).toBeNull());
    fireEvent.click(agent);
    fireEvent.change(await screen.findByPlaceholderText("Codexへ依頼…"), {
      target: { value: "こんにちは" },
    });
    fireEvent.click(screen.getByRole("button", { name: "送信" }));

    await waitFor(() =>
      expect(fetch).toHaveBeenCalledWith(
        "/api/agent-codex/whub-dev/TASK-099/turns",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ prompt: "こんにちは" }),
        },
      ),
    );
  });

  it("Codex App Serverのエラーを表示する", async () => {
    agentError = "Codex App Server returned invalid JSON";
    renderPage();

    await screen.findByRole("button", { name: "Terminal" });
    const agent = screen.getByRole("button", { name: "Agent" });
    await waitFor(() => expect(agent.getAttribute("disabled")).toBeNull());
    fireEvent.click(agent);

    expect(
      await screen.findByText("Codex App Server returned invalid JSON"),
    ).toBeTruthy();
  });
});
