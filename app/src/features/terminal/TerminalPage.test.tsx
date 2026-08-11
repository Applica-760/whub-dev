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
let operationStarts = 0;
let operatorTerminals: { operator_id: string }[] = [];
let deferSessions = false;
let deferredSessionProject: string | null = null;
let changedFiles: {
  path: string;
  status: string;
  previous_path: string | null;
  agent_generated?: boolean;
}[] = [{ path: "src/main.py", status: "M", previous_path: null }];
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
    resizeSignal,
    taskId,
  }: {
    label?: string;
    project?: string;
    resizeSignal: string;
    taskId?: string;
  }) => {
    const terminal = label ?? `${project} / ${taskId}`;
    useEffect(() => {
      terminalMounts.push(terminal);
      return () => {
        terminalUnmounts.push(terminal);
      };
    }, []);
    return (
      <div className="xterm-view" data-resize-signal={resizeSignal}>
        {terminal}
      </div>
    );
  },
}));

vi.mock("../tasks/TaskDependencyGraphWidget", () => ({
  TaskDependencyGraphWidget: ({
    onSelectTask,
    project,
  }: {
    onSelectTask?: (project: string, taskId: string) => void;
    project: string | null;
  }) => (
    <button
      onClick={() => project && onSelectTask?.(project, "TASK-126")}
      type="button"
    >
      Task graph: {project ?? "-"}
    </button>
  ),
}));

beforeEach(() => {
  operationStarts = 0;
  operatorTerminals = [];
  deferSessions = false;
  deferredSessionProject = null;
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
          json: async () => {
            approvalAttention = approvalAttention.map((item) => ({
              ...item,
              acknowledged: true,
            }));
            return approvalAttention;
          },
        });
      if (url.startsWith("/api/tasks/"))
        return Promise.resolve({
          ok: true,
          json: async () => ({
            schema_version: 1,
            task: {
              id: url.includes("TASK-101")
                ? "TASK-101"
                : url.includes("TASK-126")
                  ? "TASK-126"
                  : "TASK-099",
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
      if (url === "/api/projects")
        return Promise.resolve({
          ok: true,
          json: async () => ({ projects: ["whub-dev", "vault"] }),
        });
      if (url.startsWith("/api/agent-sessions/")) {
        const project = url.split("/").at(-1);
        if (deferSessions || project === deferredSessionProject)
          return new Promise(() => {});
        return Promise.resolve({
          ok: true,
          json: async () => ({
            sessions:
              project === "whub-dev"
                ? [
                    {
                      project: "whub-dev",
                      task_id: "TASK-099",
                      workspace_path: "projects/worktrees/whub-dev-099",
                    },
                  ]
                : [
                    {
                      project: "vault",
                      task_id: "TASK-101",
                      workspace_path: "projects/worktrees/vault-101",
                    },
                  ],
          }),
        });
      }
      return Promise.resolve({
        ok: true,
        json: async () => ({}),
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
    expect(await screen.findByText("TASK-099(in_progress)")).toBeTruthy();
    expect(screen.getByText("Task graph: whub-dev")).toBeTruthy();
    expect(await screen.findByText("src")).toBeTruthy();
    expect(await screen.findByText("new")).toBeTruthy();
    expect(
      container.querySelector(".diff-addition .diff-line-prefix")?.textContent,
    ).toBe("+");
    expect(screen.getByText("unchanged")).toBeTruthy();
    expect(container.querySelectorAll(".terminal-layout")).toHaveLength(1);
    expect(container.querySelectorAll(".terminal-task-panel")).toHaveLength(1);
    expect(container.querySelectorAll(".terminal-task-graph")).toHaveLength(1);
    expect(container.querySelectorAll(".terminal-task-detail")).toHaveLength(1);
    expect(container.querySelectorAll(".terminal-diff-layout")).toHaveLength(1);

    fireEvent.click(secondTerminal);

    expect(firstTerminal.getAttribute("aria-pressed")).toBe("false");
    expect(secondTerminal.getAttribute("aria-pressed")).toBe("true");
    expect(screen.getAllByText("vault / TASK-101")).not.toHaveLength(0);
    expect(screen.getByText("Task graph: vault")).toBeTruthy();
    expect(await screen.findByText("TASK-101(in_progress)")).toBeTruthy();
    fireEvent.click(screen.getByText("Task graph: vault"));
    expect(screen.getByText("TASK-101(in_progress)")).toBeTruthy();
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

  it("Agent生成物だけの祖先を初期展開せず、手動展開は維持する", async () => {
    changedFiles = [
      {
        path: ".agents/AGENTS_context.md",
        status: "M",
        previous_path: null,
        agent_generated: true,
      },
      {
        path: "src/main.py",
        status: "M",
        previous_path: null,
        agent_generated: false,
      },
    ];
    renderPage();

    const agents = await screen.findByText(".agents");
    expect(await screen.findByText("main.py")).toBeTruthy();
    expect(screen.queryByText("AGENTS_context.md")).toBeNull();

    fireEvent.click(agents);

    expect(await screen.findByText("AGENTS_context.md")).toBeTruthy();
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

  it("Operationではwhub-devのグラフ選択後にTask詳細を表示する", async () => {
    operatorTerminals = [{ operator_id: "operator-1" }];
    renderPage();

    const graph = await screen.findByText("Task graph: whub-dev");
    expect(screen.getByText("グラフからTaskを選択してください")).toBeTruthy();
    expect(screen.queryByText("Task ID: TASK-126")).toBeNull();

    fireEvent.click(graph);

    expect(await screen.findByText("TASK-126(in_progress)")).toBeTruthy();
    expect(fetch).toHaveBeenCalledWith(
      "/api/tasks/TASK-126?project=whub-dev",
      undefined,
    );
  });

  it("worktreeの探索中でも既存Operationを先に表示する", async () => {
    operatorTerminals = [{ operator_id: "operator-1" }];
    deferSessions = true;

    renderPage();

    expect(await screen.findByText("Operation / workspace-hub")).toBeTruthy();
    expect(screen.getByText("Agent sessionを読み込んでいます…")).toBeTruthy();
    expect(
      screen
        .getByRole("button", { name: /Operation 1/ })
        .getAttribute("aria-pressed"),
    ).toBe("true");
  });

  it("遅いProjectを待たずに取得済みAgent sessionを表示する", async () => {
    deferredSessionProject = "vault";
    renderPage();

    expect(
      await screen.findByRole("button", { name: /whub-dev.*TASK-099/ }),
    ).toBeTruthy();
    expect(screen.getByText("Agent sessionを読み込んでいます…")).toBeTruthy();
    expect(screen.queryByText("vault / TASK-101")).toBeNull();
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

  it("xterm上の⌘⇧↑↓でTerminalを切り替える", async () => {
    renderPage();

    const first = await screen.findByText("whub-dev / TASK-099");
    fireEvent.keyDown(first, {
      code: "ArrowDown",
      key: "ArrowDown",
      metaKey: true,
      shiftKey: true,
    });
    expect(await screen.findByText("vault / TASK-101")).toBeTruthy();

    fireEvent.keyDown(screen.getByText("vault / TASK-101"), {
      code: "ArrowUp",
      key: "ArrowUp",
      metaKey: true,
      shiftKey: true,
    });
    expect(await screen.findByText("whub-dev / TASK-099")).toBeTruthy();
  });

  it("xterm上の⌘⇧OでOperationを起動する", async () => {
    renderPage();

    fireEvent.keyDown(await screen.findByText("whub-dev / TASK-099"), {
      code: "KeyO",
      key: "O",
      metaKey: true,
      shiftKey: true,
    });

    await waitFor(() =>
      expect(fetch).toHaveBeenCalledWith("/api/operator-terminals", {
        method: "POST",
      }),
    );
    expect(await screen.findByText("Operation / workspace-hub")).toBeTruthy();
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

  it("ブラウザタブ復帰時に選択済みTerminalを既読化する", async () => {
    approvalAttention = [
      {
        target: "worktree",
        event: "response_completed",
        project: "whub-dev",
        task_id: "TASK-099",
        operator_id: null,
        tool_name: null,
        requested_at: "2026-08-03T00:00:00+00:00",
        acknowledged: false,
      },
    ];
    Object.defineProperty(document, "visibilityState", {
      configurable: true,
      value: "hidden",
    });
    renderPage();
    await screen.findByText("応答終了");

    Object.defineProperty(document, "visibilityState", {
      configurable: true,
      value: "visible",
    });
    fireEvent(document, new Event("visibilitychange"));

    await waitFor(() =>
      expect(fetch).toHaveBeenCalledWith(
        "/api/agent-attention/whub-dev/TASK-099/acknowledge",
        { method: "POST" },
      ),
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

  it("左右ペインの折りたたみ状態をTerminalのresize signalへ反映する", async () => {
    const view = renderPage();
    const terminal = await screen.findByText("whub-dev / TASK-099");
    expect(terminal.getAttribute("data-resize-signal")).toContain(
      ":false:false",
    );

    view.rerender(
      <MantineProvider env="test">
        <TerminalPage collapsed={{ left: true, right: false }} />
      </MantineProvider>,
    );

    expect(terminal.getAttribute("data-resize-signal")).toContain(
      ":true:false",
    );
  });
});
