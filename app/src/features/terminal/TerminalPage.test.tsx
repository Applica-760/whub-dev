import { MantineProvider } from "@mantine/core";
import {
  act,
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
    issue_number: 101,
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
let failedSessionProject: string | null = null;
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
    issueNumber,
  }: {
    active?: boolean;
    endpoint?: string;
    project?: string;
    resizeSignal: string;
    issueNumber?: number;
  }) => {
    const terminal = endpoint
      ? "Operation terminal"
      : `${project} / ${issueNumber}`;
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

beforeEach(() => {
  operationStarts = 0;
  operatorTerminals = [];
  deferSessions = false;
  deferredSessionProject = null;
  failedSessionProject = null;
  includeSessionlessProject = false;
  terminalMounts = [];
  terminalActiveAtMount = [];
  terminalUnmounts = [];
  approvalAttention = [
    {
      target: "worktree",
      event: "permission_request",
      project: "vault",
      issue_number: 101,
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
      if (url.startsWith("/api/issues/"))
        return Promise.resolve({
          ok: true,
          json: async () => [
            {
              number: 28,
              title: "Issue list",
              url: "https://github.com/Applica-760/whub/issues/28",
            },
          ],
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
        if (project === failedSessionProject)
          return Promise.reject(new Error("unmounted"));
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
                        issue_number: 99,
                        workspace_path: "projects/worktrees/whub-dev-099",
                      },
                    ]
                  : [
                      {
                        project: "vault",
                        issue_number: 101,
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
  it("Issue一覧・端末とTerminal一覧を表示する", async () => {
    const { container } = renderPage();
    const firstTerminal = await screen.findByRole("button", {
      name: /whub.*99/,
    });
    const secondTerminal = screen.getByRole("button", {
      name: /vaul.*101/,
    });
    await waitFor(() =>
      expect(firstTerminal.getAttribute("aria-pressed")).toBe("true"),
    );
    expect(firstTerminal.textContent).toBe("whub99");
    expect(secondTerminal.textContent).toBe("vaul101");
    expect(
      firstTerminal.querySelectorAll(".terminal-attention-dot"),
    ).toHaveLength(2);
    expect(screen.getByText("whub-dev / 99")).toBeTruthy();
    expect(
      await screen.findByRole("link", { name: "#28 Issue list" }),
    ).toBeTruthy();
    expect(container.querySelectorAll(".terminal-layout")).toHaveLength(1);
    expect(container.querySelectorAll(".terminal-task-panel")).toHaveLength(1);
    expect(container.querySelectorAll(".terminal-diff-layout")).toHaveLength(1);
    expect(terminalMounts).toEqual(["whub-dev / 99"]);

    fireEvent.click(secondTerminal);

    expect(firstTerminal.getAttribute("aria-pressed")).toBe("false");
    expect(secondTerminal.getAttribute("aria-pressed")).toBe("true");
    expect(screen.getAllByText("vault / 101")).not.toHaveLength(0);
    expect(
      await screen.findByRole("link", { name: "#28 Issue list" }),
    ).toBeTruthy();
    expect(terminalMounts).toEqual(["whub-dev / 99", "vault / 101"]);
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
    expect(screen.queryByText("whub-dev / 99")).toBeNull();
    expect(terminalMounts).toEqual([]);

    fireEvent.keyDown(document, {
      code: "KeyE",
      key: "E",
      metaKey: true,
      shiftKey: true,
    });

    const terminal = await screen.findByText("whub-dev / 99");
    expect(terminal.dataset.active).toBe("true");
    expect(terminalMounts).toEqual(["whub-dev / 99"]);
  });

  it("worktree parentがないProjectをExplorerの警告にしない", async () => {
    includeSessionlessProject = true;
    renderPage("/terminal/explorer");

    await waitFor(() =>
      expect(fetch).toHaveBeenCalledWith("/api/agent-sessions/portfolio", {
        signal: expect.any(AbortSignal),
      }),
    );
    await waitFor(() => expect(screen.queryByText("読込中…")).toBeNull());
    expect(screen.queryByText(/portfolio:/)).toBeNull();
  });

  it("unmount中のProjectをExplorerの警告にしない", async () => {
    failedSessionProject = "vault";
    renderPage();

    await screen.findByRole("button", { name: /whub.*99/ });
    await waitFor(() => expect(screen.queryByText("読込中…")).toBeNull());
    expect(screen.queryByText(/vault:/)).toBeNull();
  });

  it("⌘⇧EをTerminal内の任意の位置からExplorerへ遷移する", async () => {
    renderPage();
    await screen.findByText("whub-dev / 99");
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
    expect(terminalMounts).toEqual(["whub-dev / 99"]);
    expect(terminalUnmounts).toEqual([]);
    expect(screen.getByText("whub-dev / 99").dataset.active).toBe("false");

    fireEvent.keyDown(document, {
      code: "KeyE",
      key: "E",
      metaKey: true,
      shiftKey: true,
    });

    expect(await screen.findByText("whub-dev / 99")).toBeTruthy();
    expect(terminalMounts).toEqual(["whub-dev / 99"]);
    expect(terminalUnmounts).toEqual([]);
    expect(screen.getByText("whub-dev / 99").dataset.active).toBe("true");
  });

  it("見出しなしで複数Operationを短い名前で表示する", async () => {
    operatorTerminals = [
      { operator_id: "operator-1" },
      { operator_id: "operator-2" },
    ];
    renderPage();

    expect(await screen.findByRole("button", { name: /term1/ })).toBeTruthy();
    expect(screen.getByRole("button", { name: /term2/ })).toBeTruthy();
    expect(screen.queryByText("Operations")).toBeNull();
    expect(
      screen.queryByRole("button", { name: "Operationを起動" }),
    ).toBeNull();
    expect(
      screen.queryByRole("button", { name: /Operation .*を停止/ }),
    ).toBeNull();
    expect(screen.queryByRole("button", { name: /再読み込み/ })).toBeNull();
  });

  it("選択中OperationをクリックするとTerminalだけを再読み込みする", async () => {
    operatorTerminals = [{ operator_id: "operator-1" }];
    renderPage();

    expect(await screen.findByText("Operation terminal")).toBeTruthy();
    expect(terminalMounts).toEqual(["Operation terminal"]);

    fireEvent.click(screen.getByRole("button", { name: /term1/ }));

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

  it("非選択Worktreeをクリックすると可視状態で再読み込みする", async () => {
    renderPage();
    await screen.findByRole("button", {
      name: /whub.*99/,
    });
    const secondTerminal = screen.getByRole("button", {
      name: /vaul.*101/,
    });

    fireEvent.keyDown(screen.getByText("whub-dev / 99"), {
      code: "ArrowDown",
      key: "ArrowDown",
      metaKey: true,
      shiftKey: true,
    });
    fireEvent.keyDown(await screen.findByText("vault / 101"), {
      code: "ArrowUp",
      key: "ArrowUp",
      metaKey: true,
      shiftKey: true,
    });
    expect(terminalUnmounts).toEqual([]);

    fireEvent.click(secondTerminal);

    await waitFor(() =>
      expect(secondTerminal.getAttribute("aria-pressed")).toBe("true"),
    );
    expect(screen.getByText("vault / 101").dataset.active).toBe("true");
    expect(screen.getByText("whub-dev / 99").dataset.active).toBe("false");
    expect(terminalMounts).toEqual([
      "whub-dev / 99",
      "vault / 101",
      "vault / 101",
    ]);
    expect(terminalActiveAtMount).toEqual([true, true, true]);
    expect(terminalUnmounts).toEqual(["vault / 101"]);
  });

  it("worktreeの探索中でも既存Operationを先に表示する", async () => {
    operatorTerminals = [{ operator_id: "operator-1" }];
    deferSessions = true;

    renderPage();

    expect(await screen.findByText("Operation terminal")).toBeTruthy();
    expect(screen.getByText("読込中…")).toBeTruthy();
    expect(
      screen
        .getByRole("button", { name: /term1/ })
        .getAttribute("aria-pressed"),
    ).toBe("true");
  });

  it("worktreeの探索が遅くても読込中表示を5秒で消す", () => {
    deferSessions = true;
    const setTimeout = vi.spyOn(window, "setTimeout");
    renderPage();

    expect(screen.getByText("読込中…")).toBeTruthy();
    const loadingTimeout = setTimeout.mock.calls.find(
      ([, delay]) => delay === 5_000,
    );
    expect(loadingTimeout).toBeTruthy();
    act(() => (loadingTimeout?.[0] as () => void)());
    expect(screen.queryByText("読込中…")).toBeNull();
  });

  it("遅いProjectを待たずに取得済みAgent sessionを表示する", async () => {
    deferredSessionProject = "vault";
    renderPage();

    expect(
      await screen.findByRole("button", { name: /whub.*99/ }),
    ).toBeTruthy();
    expect(screen.getByText("読込中…")).toBeTruthy();
    expect(screen.queryByText("vault / 101")).toBeNull();
  });

  it("権限待ちと完了の通知枠を固定して縦に並べる", async () => {
    renderPage();

    const dot = await screen.findByRole("img", { name: "権限待ち" });
    expect(dot.dataset.event).toBe("permission_request");
    const row = screen.getByRole("button", { name: /vaul.*101/ });
    const slots = row.querySelectorAll(".terminal-attention-dot");
    expect(slots).toHaveLength(2);
    expect(slots[0].getAttribute("data-active")).toBe("true");
    expect(slots[1].getAttribute("data-active")).toBeNull();
    expect(screen.queryByText("承認待ちのTerminalがあります")).toBeNull();

    fireEvent.click(row);

    expect(await screen.findByText("vault / 101")).toBeTruthy();
    await waitFor(() =>
      expect(fetch).toHaveBeenCalledWith(
        "/api/agent-attention/vault/101/acknowledge",
        { method: "POST" },
      ),
    );
  });

  it("xterm上の⌘⇧↑↓でTerminalを切り替える", async () => {
    renderPage();

    const first = await screen.findByText("whub-dev / 99");
    fireEvent.keyDown(first, {
      code: "ArrowDown",
      key: "ArrowDown",
      metaKey: true,
      shiftKey: true,
    });
    expect(await screen.findByText("vault / 101")).toBeTruthy();

    fireEvent.keyDown(screen.getByText("vault / 101"), {
      code: "ArrowUp",
      key: "ArrowUp",
      metaKey: true,
      shiftKey: true,
    });
    expect(await screen.findByText("whub-dev / 99")).toBeTruthy();
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
        issue_number: null,
        operator_id: "operator-3",
        tool_name: null,
        requested_at: "2026-08-03T00:00:00+00:00",
        acknowledged: false,
      },
    ];
    renderPage();

    const dot = await screen.findByRole("img", { name: "完了" });
    expect(dot.dataset.event).toBe("response_completed");
    fireEvent.click(await screen.findByText("term1"));

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
        issue_number: 99,
        operator_id: null,
        tool_name: "Bash",
        requested_at: "2026-08-03T00:00:00+00:00",
        acknowledged: false,
      },
    ];

    renderPage();

    expect(await screen.findByRole("img", { name: "権限待ち" })).toBeTruthy();
    expect(fetch).not.toHaveBeenCalledWith(
      "/api/agent-attention/whub-dev/99/acknowledge",
      { method: "POST" },
    );
  });

  it("ブラウザタブ復帰時に選択済みTerminalを既読化する", async () => {
    approvalAttention = [
      {
        target: "worktree",
        event: "response_completed",
        project: "whub-dev",
        issue_number: 99,
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
    await screen.findByRole("img", { name: "完了" });
    await screen.findByText("whub-dev / 99");

    Object.defineProperty(document, "visibilityState", {
      configurable: true,
      value: "visible",
    });
    await waitFor(() => {
      fireEvent(document, new Event("visibilitychange"));
      expect(fetch).toHaveBeenCalledWith(
        "/api/agent-attention/whub-dev/99/acknowledge",
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
        issue_number: 99,
        operator_id: null,
        tool_name: "Bash",
        requested_at: "2026-08-03T00:00:00+00:00",
        acknowledged: false,
      },
    ];
    renderPage();

    fireEvent.click(await screen.findByRole("button", { name: /whub.*99/ }));

    await waitFor(() =>
      expect(fetch).toHaveBeenCalledWith(
        "/api/agent-attention/whub-dev/99/acknowledge",
        { method: "POST" },
      ),
    );
  });

  it("左右ペインの折りたたみ状態をTerminalのresize signalへ反映する", async () => {
    const view = renderPage();
    const terminal = await screen.findByText("whub-dev / 99");
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
