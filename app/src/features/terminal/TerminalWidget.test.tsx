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
  write: vi.fn(),
}));

vi.mock("@xterm/xterm", () => ({
  Terminal: class {
    cols = 80;
    rows = 24;

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

class FakeWebSocket {
  static readonly CONNECTING = 0;
  static readonly OPEN = 1;
  static readonly CLOSED = 3;
  static instances: FakeWebSocket[] = [];

  readonly sent: string[] = [];
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

  message(data: string) {
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
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("TerminalWidget", () => {
  it("接続中の入力を捨て、接続後は構造化frameを送り、破棄時にleaseを解放する", () => {
    const view = render(
      <MantineProvider env="test">
        <TerminalWidget
          project="whub-dev"
          resizeSignal="false:false"
          taskId="TASK-100"
        />
      </MantineProvider>,
    );
    const socket = FakeWebSocket.instances[0];

    act(() => terminalMocks.inputHandler?.("before-open"));
    expect(socket.sent).toEqual([]);

    act(() => socket.open());
    act(() => terminalMocks.inputHandler?.("1"));
    act(() => socket.message("echo"));

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

  it("親layoutの変更後に再fitしてtmuxへresizeを送る", () => {
    const view = render(
      <MantineProvider env="test">
        <TerminalWidget
          project="whub-dev"
          resizeSignal="false:false"
          taskId="TASK-100"
        />
      </MantineProvider>,
    );
    const socket = FakeWebSocket.instances[0];
    act(() => socket.open());
    terminalMocks.fit.mockClear();

    view.rerender(
      <MantineProvider env="test">
        <TerminalWidget
          project="whub-dev"
          resizeSignal="true:true"
          taskId="TASK-100"
        />
      </MantineProvider>,
    );

    expect(FakeWebSocket.instances).toHaveLength(1);
    expect(terminalMocks.fit).toHaveBeenCalledOnce();
    expect(JSON.parse(socket.sent.at(-1) ?? "{}")).toEqual({
      type: "resize",
      columns: 80,
      rows: 24,
    });
    expect(
      view.container.querySelector('div[style*="height: 64rem"]'),
    ).toBeTruthy();
  });
});
