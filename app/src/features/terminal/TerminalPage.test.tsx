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
  agentError = null;
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
    expect(screen.getAllByText("vault / TASK-101")).not.toHaveLength(0);
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

  it("承認待ちのTerminalをバッジと導線で示す", async () => {
    renderPage();

    expect(
      await screen.findByText("承認待ちのTerminalがあります"),
    ).toBeTruthy();
    expect(screen.getByText("承認待ち")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Terminalを開く" }));

    expect(await screen.findByText("vault / TASK-101")).toBeTruthy();
    await waitFor(() =>
      expect(fetch).toHaveBeenCalledWith(
        "/api/agent-attention/vault/TASK-101/acknowledge",
        { method: "POST" },
      ),
    );
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

    fireEvent.click(agent);

    expect(agent.getAttribute("aria-pressed")).toBe("true");
    expect(await screen.findByPlaceholderText("Codexへ依頼…")).toBeTruthy();
  });

  it("Codex promptをJSONとして送信する", async () => {
    renderPage();

    fireEvent.click(await screen.findByRole("button", { name: "Agent" }));
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

    fireEvent.click(await screen.findByRole("button", { name: "Agent" }));

    expect(
      await screen.findByText("Codex App Server returned invalid JSON"),
    ).toBeTruthy();
  });
});
