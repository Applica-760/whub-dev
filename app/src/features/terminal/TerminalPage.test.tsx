import { MantineProvider } from "@mantine/core";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { useEffect } from "react";
import { MemoryRouter } from "react-router";
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
let includeSessionlessProject = false;
let terminalMounts: string[] = [];
let terminalActiveAtMount: boolean[] = [];
let terminalUnmounts: string[] = [];

vi.mock("./TerminalWidget", () => ({
  TerminalWidget: ({
    active,
    endpoint,
    project,
    resizeSignal,
    taskId,
  }: {
    active?: boolean;
    endpoint?: string;
    project?: string;
    resizeSignal: string;
    taskId?: string;
  }) => {
    const terminal = endpoint ? "Operation terminal" : `${project} / ${taskId}`;
    useEffect(() => {
      terminalMounts.push(terminal);
      terminalActiveAtMount.push(Boolean(active));
      return () => {
        terminalUnmounts.push(terminal);
      };
    }, []);
    return (
      <div
        className="xterm-view"
        data-active={active}
        data-resize-signal={resizeSignal}
      >
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
  includeSessionlessProject = false;
  terminalMounts = [];
  terminalActiveAtMount = [];
  terminalUnmounts = [];
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
      if (url.startsWith("/api/tasks/active?"))
        return Promise.resolve({
          ok: true,
          json: async () => ({ tasks: [] }),
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
      if (url.startsWith("/api/hub-explorer/directory"))
        return Promise.resolve({
          ok: true,
          json: async () => ({ entries: [] }),
        });
      if (url === "/api/projects")
        return Promise.resolve({
          ok: true,
          json: async () => ({
            projects: [
              "whub-dev",
              "vault",
              ...(includeSessionlessProject ? ["portfolio"] : []),
            ],
          }),
        });
      if (url.startsWith("/api/agent-sessions/")) {
        const project = url.split("/").at(-1);
        if (deferSessions || project === deferredSessionProject)
          return new Promise(() => {});
        return Promise.resolve({
          ok: true,
          json: async () => ({
            sessions:
              project === "portfolio"
                ? []
                : project === "whub-dev"
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

function renderPage(path = "/terminal") {
  return render(
    <MantineProvider env="test">
      <MemoryRouter initialEntries={[path]}>
        <TerminalPage />
      </MemoryRouter>
    </MantineProvider>,
  );
}

describe("TerminalPage", () => {
  it("Task詳細・端末とTerminal一覧を表示する", async () => {
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
    expect(container.querySelectorAll(".terminal-layout")).toHaveLength(1);
    expect(container.querySelectorAll(".terminal-task-panel")).toHaveLength(1);
    expect(container.querySelectorAll(".terminal-task-graph")).toHaveLength(1);
    expect(container.querySelectorAll(".terminal-task-detail")).toHaveLength(1);
    expect(container.querySelectorAll(".terminal-diff-layout")).toHaveLength(1);
    expect(terminalMounts).toEqual(["whub-dev / TASK-099"]);

    fireEvent.click(secondTerminal);

    expect(firstTerminal.getAttribute("aria-pressed")).toBe("false");
    expect(secondTerminal.getAttribute("aria-pressed")).toBe("true");
    expect(screen.getAllByText("vault / TASK-101")).not.toHaveLength(0);
    expect(screen.getByText("Task graph: vault")).toBeTruthy();
    expect(await screen.findByText("TASK-101(in_progress)")).toBeTruthy();
    fireEvent.click(screen.getByText("Task graph: vault"));
    expect(await screen.findByText("TASK-126(in_progress)")).toBeTruthy();
    expect(fetch).toHaveBeenCalledWith(
      "/api/tasks/active/TASK-126?project=vault",
      undefined,
    );
    expect(terminalMounts).toEqual(["whub-dev / TASK-099", "vault / TASK-101"]);
    expect(terminalUnmounts).toEqual([]);
  });

  it("直接アクセスしたExplorerではHub rootを表示する", async () => {
    renderPage("/terminal/explorer");

    expect(
      await screen.findByText("ファイルを選択してください。"),
    ).toBeTruthy();
    expect(fetch).toHaveBeenCalledWith(
      "/api/hub-explorer/directory",
      undefined,
    );
    expect(screen.queryByText("whub-dev / TASK-099")).toBeNull();
    expect(terminalMounts).toEqual([]);

    fireEvent.keyDown(document, {
      code: "KeyE",
      key: "E",
      metaKey: true,
      shiftKey: true,
    });

    const terminal = await screen.findByText("whub-dev / TASK-099");
    expect(terminal.dataset.active).toBe("true");
    expect(terminalMounts).toEqual(["whub-dev / TASK-099"]);
  });

  it("worktree parentがないProjectをExplorerの警告にしない", async () => {
    includeSessionlessProject = true;
    renderPage("/terminal/explorer");

    await waitFor(() =>
      expect(fetch).toHaveBeenCalledWith(
        "/api/agent-sessions/portfolio",
        undefined,
      ),
    );
    await waitFor(() =>
      expect(screen.queryByText("Agent sessionを読み込んでいます…")).toBeNull(),
    );
    expect(screen.queryByText(/portfolio:/)).toBeNull();
  });

  it("⌘⇧EをTerminal内の任意の位置からExplorerへ遷移する", async () => {
    renderPage();
    await screen.findByText("whub-dev / TASK-099");
    await waitFor(() =>
      expect(fetch).toHaveBeenCalledWith(
        "/api/hub-explorer/directory",
        undefined,
      ),
    );
    const hubRequests = () =>
      vi
        .mocked(fetch)
        .mock.calls.filter(([input]) =>
          String(input).startsWith("/api/hub-explorer"),
        ).length;
    expect(hubRequests()).toBe(1);

    fireEvent.keyDown(document, {
      code: "KeyE",
      key: "E",
      metaKey: true,
      shiftKey: true,
    });

    expect(
      await screen.findByText("ファイルを選択してください。"),
    ).toBeTruthy();
    expect(hubRequests()).toBe(1);
    expect(terminalMounts).toEqual(["whub-dev / TASK-099"]);
    expect(terminalUnmounts).toEqual([]);
    expect(screen.getByText("whub-dev / TASK-099").dataset.active).toBe(
      "false",
    );

    fireEvent.keyDown(document, {
      code: "KeyE",
      key: "E",
      metaKey: true,
      shiftKey: true,
    });

    expect(await screen.findByText("whub-dev / TASK-099")).toBeTruthy();
    expect(terminalMounts).toEqual(["whub-dev / TASK-099"]);
    expect(terminalUnmounts).toEqual([]);
    expect(screen.getByText("whub-dev / TASK-099").dataset.active).toBe("true");
  });

  it("複数Operationを起動・選択・個別終了できる", async () => {
    renderPage();
    const start = await screen.findByRole("button", {
      name: "Operationを起動",
    });
    fireEvent.click(start);
    expect(await screen.findByText("Operation terminal")).toBeTruthy();

    fireEvent.click(start);
    expect(
      await screen.findByRole("button", { name: "Operation operator-2を停止" }),
    ).toBeTruthy();
    fireEvent.click(
      screen.getByRole("button", { name: "Operation operator-1を停止" }),
    );

    await waitFor(() =>
      expect(fetch).toHaveBeenCalledWith("/api/operator-terminals/operator-1", {
        method: "DELETE",
      }),
    );
    expect(
      screen.queryByRole("button", { name: "Operation operator-1を停止" }),
    ).toBeNull();
  });

  it("選択中OperationのTerminalだけを再読み込みする", async () => {
    operatorTerminals = [{ operator_id: "operator-1" }];
    renderPage();

    expect(await screen.findByText("Operation terminal")).toBeTruthy();
    expect(terminalMounts).toEqual(["Operation terminal"]);

    fireEvent.click(
      screen.getByRole("button", {
        name: "Operationを再読み込み: operator-1",
      }),
    );

    await waitFor(() =>
      expect(terminalUnmounts).toEqual(["Operation terminal"]),
    );
    expect(terminalMounts).toEqual([
      "Operation terminal",
      "Operation terminal",
    ]);
    expect(terminalActiveAtMount).toEqual([true, true]);
    expect(
      vi.mocked(fetch).mock.calls.some(([, init]) => init?.method === "DELETE"),
    ).toBe(false);
  });

  it("非選択Worktreeを選択して可視状態で再読み込みする", async () => {
    renderPage();
    const firstTerminal = await screen.findByRole("button", {
      name: /whub-dev.*TASK-099/,
    });
    const secondTerminal = screen.getByRole("button", {
      name: /vault.*TASK-101/,
    });

    fireEvent.click(secondTerminal);
    await waitFor(() =>
      expect(secondTerminal.getAttribute("aria-pressed")).toBe("true"),
    );
    fireEvent.click(firstTerminal);
    await waitFor(() =>
      expect(firstTerminal.getAttribute("aria-pressed")).toBe("true"),
    );

    fireEvent.click(
      screen.getByRole("button", {
        name: "Terminalを再読み込み: TASK-101 (vault)",
      }),
    );

    await waitFor(() =>
      expect(secondTerminal.getAttribute("aria-pressed")).toBe("true"),
    );
    expect(screen.getByText("vault / TASK-101").dataset.active).toBe("true");
    expect(screen.getByText("whub-dev / TASK-099").dataset.active).toBe(
      "false",
    );
    expect(terminalMounts).toEqual([
      "whub-dev / TASK-099",
      "vault / TASK-101",
      "vault / TASK-101",
    ]);
    expect(terminalActiveAtMount).toEqual([true, true, true]);
    expect(terminalUnmounts).toEqual(["vault / TASK-101"]);
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
      "/api/tasks/active/TASK-126?project=whub-dev",
      undefined,
    );
  });

  it("worktreeの探索中でも既存Operationを先に表示する", async () => {
    operatorTerminals = [{ operator_id: "operator-1" }];
    deferSessions = true;

    renderPage();

    expect(await screen.findByText("Operation terminal")).toBeTruthy();
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

  it("⌘⇧OでOperationを起動する", async () => {
    renderPage();

    fireEvent.keyDown(document, {
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
    expect(await screen.findByText("Operation terminal")).toBeTruthy();
  });

  it("xterm上の⌘⇧Xで選択中のOperationを終了する", async () => {
    operatorTerminals = [{ operator_id: "operator-1" }];
    renderPage();

    fireEvent.keyDown(await screen.findByText("Operation terminal"), {
      code: "KeyX",
      key: "X",
      metaKey: true,
      shiftKey: true,
    });

    await waitFor(() =>
      expect(fetch).toHaveBeenCalledWith("/api/operator-terminals/operator-1", {
        method: "DELETE",
      }),
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
    await screen.findByText("whub-dev / TASK-099");

    Object.defineProperty(document, "visibilityState", {
      configurable: true,
      value: "visible",
    });
    await waitFor(() => {
      fireEvent(document, new Event("visibilitychange"));
      expect(fetch).toHaveBeenCalledWith(
        "/api/agent-attention/whub-dev/TASK-099/acknowledge",
        { method: "POST" },
      );
    });
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
        <MemoryRouter initialEntries={["/terminal"]}>
          <TerminalPage collapsed={{ left: true, right: false }} />
        </MemoryRouter>
      </MantineProvider>,
    );

    expect(terminal.getAttribute("data-resize-signal")).toContain(
      ":true:false",
    );
  });
});
