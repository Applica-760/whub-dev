import { MantineProvider } from "@mantine/core";
import { act, cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { TerminalWidget } from "./TerminalWidget";

const terminalMocks = vi.hoisted(() => ({
  dispose: vi.fn(),
  fit: vi.fn(),
  focus: vi.fn(),
  inputDispose: vi.fn(),
  inputHandler: undefined as ((data: string) => void) | undefined,
  linkHandler: undefined as
    ((event: MouseEvent, uri: string) => void) | undefined,
  options: undefined as unknown,
  write: vi.fn(),
}));

vi.mock("@xterm/xterm", () => ({
  Terminal: class {
    cols = 80;
    rows = 24;

    constructor(options: unknown) {
      terminalMocks.options = options;
    }

    dispose = terminalMocks.dispose;
    focus = terminalMocks.focus;
    write = terminalMocks.write;

    loadAddon() {}
    open() {}
    onData(handler: (data: string) => void) {
      terminalMocks.inputHandler = handler;
      return { dispose: terminalMocks.inputDispose };
    }
  },
}));

vi.mock("@xterm/addon-fit", () => ({
  FitAddon: class {
    fit = terminalMocks.fit;
  },
}));

vi.mock("@xterm/addon-web-links", () => ({
  WebLinksAddon: class {
    constructor(handler: (event: MouseEvent, uri: string) => void) {
      terminalMocks.linkHandler = handler;
    }
  },
}));

class FakeWebSocket {
  static readonly CONNECTING = 0;
  static readonly OPEN = 1;
  static readonly CLOSED = 3;
  static instances: FakeWebSocket[] = [];

  readonly sent: string[] = [];
  binaryType: BinaryType = "blob";
  readyState = FakeWebSocket.CONNECTING;
  private readonly listeners = new Map<string, Array<(event: Event) => void>>();

  constructor(readonly url: string) {
    FakeWebSocket.instances.push(this);
  }

  addEventListener(type: string, listener: (event: Event) => void) {
    const listeners = this.listeners.get(type) ?? [];
    listeners.push(listener);
    this.listeners.set(type, listeners);
  }

  send(data: string) {
    this.sent.push(data);
  }

  close() {
    this.readyState = FakeWebSocket.CLOSED;
    this.dispatch("close", new Event("close"));
  }

  open() {
    this.readyState = FakeWebSocket.OPEN;
    this.dispatch("open", new Event("open"));
  }

  message(data: ArrayBuffer | string) {
    this.dispatch("message", new MessageEvent("message", { data }));
  }

  private dispatch(type: string, event: Event) {
    for (const listener of this.listeners.get(type) ?? []) {
      listener(event);
    }
  }
}

beforeEach(() => {
  FakeWebSocket.instances = [];
  terminalMocks.inputHandler = undefined;
  terminalMocks.linkHandler = undefined;
  terminalMocks.options = undefined;
  vi.clearAllMocks();
  vi.stubGlobal("WebSocket", FakeWebSocket);
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
      disconnect() {}
    },
  );
  vi.stubGlobal(
    "requestAnimationFrame",
    vi.fn((callback: FrameRequestCallback) => {
      callback(0);
      return 1;
    }),
  );
  vi.stubGlobal("cancelAnimationFrame", vi.fn());
  vi.stubGlobal("open", vi.fn());
});

afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe("TerminalWidget", () => {
  it("接続前の入力失敗を表示し、接続後は構造化frameを送り、破棄時にleaseを解放する", () => {
    const view = render(
      <MantineProvider env="test">
        <TerminalWidget
          project="whub-dev"
          resizeSignal="false:false"
          issueNumber={100}
        />
      </MantineProvider>,
    );
    const socket = FakeWebSocket.instances[0];

    act(() => terminalMocks.inputHandler?.("before-open"));
    expect(socket.sent).toEqual([]);
    expect(
      screen.getByText("端末に未接続のため入力を送信できません。"),
    ).toBeTruthy();

    act(() => socket.open());
    act(() => terminalMocks.inputHandler?.("1"));
    act(() => socket.message(new TextEncoder().encode("echo").buffer));

    expect(socket.sent.map((frame) => JSON.parse(frame))).toEqual([
      { type: "claim" },
      { type: "resize", columns: 80, rows: 24 },
      { type: "input", data: "1" },
    ]);
    expect(terminalMocks.write).toHaveBeenCalledWith("echo");

    view.unmount();

    expect(JSON.parse(socket.sent.at(-1) ?? "{}")).toEqual({ type: "release" });
    expect(socket.readyState).toBe(FakeWebSocket.CLOSED);
    expect(screen.queryByText("端末接続が切断されました。")).toBeNull();
  });

  it("切断後に再接続してcontrollerを再取得し、protocol errorを表示する", () => {
    vi.useFakeTimers();
    render(
      <MantineProvider env="test">
        <TerminalWidget
          project="whub-dev"
          resizeSignal="initial"
          issueNumber={100}
        />
      </MantineProvider>,
    );
    const first = FakeWebSocket.instances[0];
    act(() => first.open());

    act(() => first.close());
    expect(screen.getByText("端末接続が切断されました。")).toBeTruthy();
    act(() => terminalMocks.inputHandler?.("disconnected"));
    expect(
      screen.getByText("端末に未接続のため入力を送信できません。"),
    ).toBeTruthy();

    act(() => vi.advanceTimersByTime(1_000));
    const second = FakeWebSocket.instances[1];
    act(() => second.open());
    expect(JSON.parse(second.sent[0])).toEqual({ type: "claim" });

    act(() =>
      second.message(
        JSON.stringify({ type: "error", detail: "controller unavailable" }),
      ),
    );
    expect(screen.getByText("controller unavailable")).toBeTruthy();
  });

  it("非表示中はresizeとfocusを行わず、再選択してもTerminalを再生成しない", () => {
    const view = render(
      <MantineProvider env="test">
        <TerminalWidget
          active={false}
          project="whub-dev"
          resizeSignal="inactive"
          issueNumber={100}
        />
      </MantineProvider>,
    );
    const socket = FakeWebSocket.instances[0];
    act(() => socket.open());

    expect(socket.sent.map((frame) => JSON.parse(frame))).toEqual([
      { type: "claim" },
    ]);
    expect(terminalMocks.fit).not.toHaveBeenCalled();
    expect(terminalMocks.focus).not.toHaveBeenCalled();

    view.rerender(
      <MantineProvider env="test">
        <TerminalWidget
          active
          project="whub-dev"
          resizeSignal="active"
          issueNumber={100}
        />
      </MantineProvider>,
    );

    expect(FakeWebSocket.instances).toHaveLength(1);
    expect(terminalMocks.dispose).not.toHaveBeenCalled();
    expect(terminalMocks.fit).toHaveBeenCalledOnce();
    expect(terminalMocks.focus).toHaveBeenCalledOnce();
    expect(JSON.parse(socket.sent.at(-1) ?? "{}")).toEqual({
      type: "resize",
      columns: 80,
      rows: 24,
    });
  });

  it("分割されたUTF-8バイナリフレームを一文字として表示する", () => {
    render(
      <MantineProvider env="test">
        <TerminalWidget
          project="whub-dev"
          resizeSignal="initial"
          issueNumber={100}
        />
      </MantineProvider>,
    );
    const socket = FakeWebSocket.instances[0];
    const bytes = new TextEncoder().encode("あ");

    act(() => socket.open());
    act(() => socket.message(bytes.slice(0, 1).buffer));
    act(() => socket.message(bytes.slice(1).buffer));

    expect(socket.binaryType).toBe("arraybuffer");
    expect(terminalMocks.write).toHaveBeenLastCalledWith("あ");
  });

  it("親layoutの変更後に再fitしてtmuxへresizeを送る", () => {
    const view = render(
      <MantineProvider env="test">
        <TerminalWidget
          project="whub-dev"
          resizeSignal="false:false"
          issueNumber={100}
        />
      </MantineProvider>,
    );
    const socket = FakeWebSocket.instances[0];
    act(() => socket.open());
    terminalMocks.fit.mockClear();
    const framesBeforeRerender = socket.sent.length;

    view.rerender(
      <MantineProvider env="test">
        <TerminalWidget
          project="whub-dev"
          resizeSignal="true:true"
          issueNumber={100}
        />
      </MantineProvider>,
    );

    expect(FakeWebSocket.instances).toHaveLength(1);
    expect(terminalMocks.fit).toHaveBeenCalledOnce();
    expect(socket.sent).toHaveLength(framesBeforeRerender);
    expect(JSON.parse(socket.sent.at(-1) ?? "{}")).toEqual({
      type: "resize",
      columns: 80,
      rows: 24,
    });
    expect(view.container.querySelector(".xterm-view")).toBeTruthy();
  });

  it("修飾キー付きHTTP linkだけを開く", () => {
    render(
      <MantineProvider env="test">
        <TerminalWidget
          project="whub-dev"
          resizeSignal="false:false"
          issueNumber={100}
        />
      </MantineProvider>,
    );

    act(() =>
      terminalMocks.linkHandler?.(
        new MouseEvent("click"),
        "https://example.com/plain",
      ),
    );
    expect(window.open).not.toHaveBeenCalled();

    act(() =>
      terminalMocks.linkHandler?.(
        new MouseEvent("click", { metaKey: true }),
        "https://example.com/codex",
      ),
    );
    expect(window.open).toHaveBeenCalledWith(
      "https://example.com/codex",
      "_blank",
      "noopener,noreferrer",
    );

    act(() =>
      terminalMocks.linkHandler?.(
        new MouseEvent("click", { ctrlKey: true }),
        "file:///tmp/secret",
      ),
    );
    expect(window.open).toHaveBeenCalledOnce();
  });

  it("すべてのTerminalでOption+ドラッグ選択を有効にする", () => {
    const worktree = render(
      <MantineProvider env="test">
        <TerminalWidget
          project="whub-dev"
          resizeSignal="initial"
          issueNumber={100}
        />
      </MantineProvider>,
    );

    expect(terminalMocks.options).toMatchObject({
      macOptionClickForcesSelection: true,
    });

    worktree.unmount();
    render(
      <MantineProvider env="test">
        <TerminalWidget
          endpoint="/api/operator-terminals/operator-1"
          resizeSignal="initial"
        />
      </MantineProvider>,
    );

    expect(terminalMocks.options).toMatchObject({
      macOptionClickForcesSelection: true,
    });
  });
});
