import { MantineProvider } from "@mantine/core";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { useEffect } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { TerminalPage } from "./TerminalPage";
import type { ApprovalAttention } from "./attentionApi";

let approvalAttention: ApprovalAttention[] = [
  {
    target: "worktree",
    event: "permission_request",
    project: "vault",
    task_id: "TASK-101",
    operator_id: null,
    tool_name: "Bash",
    requested_at: "2026-08-03T00:00:00+00:00",
    acknowledged: false,
  },
];
let agentError: string | null = null;
let operationStarts = 0;
let operatorTerminals: { operator_id: string }[] = [];
let deferWorktrees = false;
let changedFiles = [{ path: "src/main.py", status: "M", previous_path: null }];
let worktreeFile: {
  path: string;
  content: string | null;
  diff: string;
  state: string;
} = {
  path: "src/main.py",
  content: "new\nunchanged\n",
  diff: "@@ -1 +1 @@\n-old\n+new",
  state: "text",
};
let clipboardWrite = vi.fn();
let terminalMounts: string[] = [];
let terminalUnmounts: string[] = [];

vi.mock("./TerminalWidget", () => ({
  TerminalWidget: ({
    label,
    project,
    taskId,
  }: {
    label?: string;
    project?: string;
    taskId?: string;
  }) => {
    const terminal = label ?? `${project} / ${taskId}`;
    useEffect(() => {
      terminalMounts.push(terminal);
      return () => {
        terminalUnmounts.push(terminal);
      };
    }, []);
    return <div>{terminal}</div>;
  },
}));

beforeEach(() => {
  agentError = null;
  operationStarts = 0;
  operatorTerminals = [];
  deferWorktrees = false;
  changedFiles = [{ path: "src/main.py", status: "M", previous_path: null }];
  worktreeFile = {
    path: "src/main.py",
    content: "new\nunchanged\n",
    diff: "@@ -1 +1 @@\n-old\n+new",
    state: "text",
  };
  clipboardWrite = vi.fn();
  terminalMounts = [];
  terminalUnmounts = [];
  Object.defineProperty(navigator, "clipboard", {
    configurable: true,
    value: { writeText: clipboardWrite },
  });
  approvalAttention = [
    {
      target: "worktree",
      event: "permission_request",
      project: "vault",
      task_id: "TASK-101",
      operator_id: null,
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
              : { terminals: operatorTerminals },
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
          json: async () =>
            approvalAttention.map((item) => ({ ...item, acknowledged: true })),
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
          json: async () => worktreeFile,
        });
      if (deferWorktrees) return new Promise(() => {});
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
    expect(screen.getByText("unchanged")).toBeTruthy();
    expect(container.querySelectorAll(".terminal-layout")).toHaveLength(1);
    expect(container.querySelectorAll(".terminal-diff-layout")).toHaveLength(1);

    fireEvent.click(secondTerminal);

    expect(firstTerminal.getAttribute("aria-pressed")).toBe("false");
    expect(secondTerminal.getAttribute("aria-pressed")).toBe("true");
    expect(screen.getAllByText("vault / TASK-101")).not.toHaveLength(0);
    expect(terminalMounts).toEqual(["whub-dev / TASK-099", "vault / TASK-101"]);
    expect(terminalUnmounts).toEqual(["whub-dev / TASK-099"]);
    expect(fetch).toHaveBeenCalledWith(
      "/api/worktrees/vault/TASK-101/changes",
      undefined,
    );
  });

  it("Git Explorerで変更ファイルへの経路を初期展開し、状態と右クリックコピーを反映する", async () => {
    changedFiles = [
      { path: "src/nested/main.py", status: "M", previous_path: null },
      { path: "draft.txt", status: "A", previous_path: null },
      { path: "unchanged/note.txt", status: "", previous_path: null },
    ];
    const { container } = renderPage();

    const source = await screen.findByText("src");
    expect(await screen.findByText("main.py")).toBeTruthy();
    expect(
      container
        .querySelector(".diff-tree-chevron")
        ?.getAttribute("data-expanded"),
    ).toBe("true");
    expect(
      container
        .querySelectorAll(".diff-tree-chevron")[1]
        ?.getAttribute("data-expanded"),
    ).toBe("true");
    expect(
      container
        .querySelectorAll(".diff-tree-chevron")[2]
        ?.getAttribute("data-expanded"),
    ).toBeNull();
    expect(container.querySelector('[data-changed="true"]')).toBeTruthy();
    expect(container.querySelector('[data-new="true"]')).toBeTruthy();

    fireEvent.click(source);
    expect(screen.queryByText("main.py")).toBeNull();
    expect(
      container
        .querySelector(".diff-tree-chevron")
        ?.getAttribute("data-expanded"),
    ).toBeNull();

    fireEvent.click(source);
    expect(await screen.findByText("main.py")).toBeTruthy();
    expect(
      container.querySelector(".diff-tree-children")?.getAttribute("style"),
    ).toBeNull();
    expect(
      container.querySelector(".diff-tree-guide")?.getAttribute("style"),
    ).toContain("inset-inline-start: 22px");
    fireEvent.contextMenu(screen.getByText("main.py"));
    expect(clipboardWrite).toHaveBeenCalledWith(
      "projects/worktrees/whub-dev-099/src/nested/main.py",
    );
  });

  it("ディレクトリを各階層でファイルより先に名前順で表示する", async () => {
    changedFiles = [
      { path: "z.txt", status: "", previous_path: null },
      { path: "src/z.py", status: "", previous_path: null },
      { path: "a.txt", status: "", previous_path: null },
      { path: "src/a.py", status: "", previous_path: null },
    ];
    const { container } = renderPage();

    await screen.findByText("src");
    const rootLabels = Array.from(
      container.querySelectorAll(".diff-tree-node"),
    ).map((node) => node.textContent?.trim());
    expect(rootLabels).toEqual(["src", "a.txt", "z.txt"]);

    fireEvent.click(screen.getByText("src"));
    const labels = Array.from(
      container.querySelectorAll(".diff-tree-node"),
    ).map((node) => node.textContent?.trim());
    expect(labels).toEqual(["src", "a.py", "z.py", "a.txt", "z.txt"]);
  });

  it("バイナリファイルの本文を表示しない", async () => {
    worktreeFile = {
      path: "src/main.py",
      content: null,
      diff: "",
      state: "binary",
    };
    renderPage();

    expect(
      await screen.findByText("バイナリファイルは表示できません。"),
    ).toBeTruthy();
  });

  it.each([
    {
      content: "",
      message: "空のファイルです。",
      state: "text",
    },
    {
      content: null,
      message: "ファイルを読み込めません。",
      state: "unreadable",
    },
  ])("$stateファイルの表示状態を示す", async ({ content, message, state }) => {
    worktreeFile = {
      path: "src/main.py",
      content,
      diff: "",
      state,
    };
    renderPage();

    expect(await screen.findByText(message)).toBeTruthy();
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

  it("worktreeの探索中でも既存Operationを先に表示する", async () => {
    operatorTerminals = [{ operator_id: "operator-1" }];
    deferWorktrees = true;

    renderPage();

    expect(await screen.findByText("Operation / workspace-hub")).toBeTruthy();
    expect(screen.getByText("worktreeを読み込んでいます…")).toBeTruthy();
    expect(
      screen
        .getByRole("button", { name: /Operation 1/ })
        .getAttribute("aria-pressed"),
    ).toBe("true");
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

  it("Operationの不変IDへ応答終了通知を表示して既読化する", async () => {
    operatorTerminals = [{ operator_id: "operator-3" }];
    approvalAttention = [
      {
        target: "operator",
        event: "response_completed",
        project: null,
        task_id: null,
        operator_id: "operator-3",
        tool_name: null,
        requested_at: "2026-08-03T00:00:00+00:00",
        acknowledged: false,
      },
    ];
    renderPage();

    expect(await screen.findByText("応答終了")).toBeTruthy();
    fireEvent.click(await screen.findByText("Operation 1"));

    await waitFor(() =>
      expect(fetch).toHaveBeenCalledWith(
        "/api/agent-attention/operator/operator-3/acknowledge",
        { method: "POST" },
      ),
    );
  });

  it("既に選択済みのTerminalへ新着の承認待ちが来ても既読化しない", async () => {
    approvalAttention = [
      {
        target: "worktree",
        event: "permission_request",
        project: "whub-dev",
        task_id: "TASK-099",
        operator_id: null,
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
        target: "worktree",
        event: "permission_request",
        project: "whub-dev",
        task_id: "TASK-099",
        operator_id: null,
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
