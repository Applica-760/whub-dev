import { act, cleanup, render } from "@testing-library/react";
import { createRef } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { XtermView } from "./XtermView";
import type { XtermViewHandle } from "./XtermView";

const xtermMocks = vi.hoisted(() => ({
  dispose: vi.fn(),
  fit: vi.fn(),
  focus: vi.fn(),
  inputDispose: vi.fn(),
  inputHandler: undefined as ((data: string) => void) | undefined,
  open: vi.fn(),
  write: vi.fn(),
}));

vi.mock("@xterm/xterm", () => ({
  Terminal: class {
    cols = 120;
    rows = 40;

    dispose = xtermMocks.dispose;
    focus = xtermMocks.focus;
    open = xtermMocks.open;
    write = xtermMocks.write;

    loadAddon() {}
    onData(handler: (data: string) => void) {
      xtermMocks.inputHandler = handler;
      return { dispose: xtermMocks.inputDispose };
    }
  },
}));

vi.mock("@xterm/addon-fit", () => ({
  FitAddon: class {
    fit = xtermMocks.fit;
  },
}));

beforeEach(() => {
  xtermMocks.inputHandler = undefined;
  vi.clearAllMocks();
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

describe("XtermView", () => {
  it("xtermの入出力・fit・focus・破棄をcomponent内で管理する", () => {
    const handle = createRef<XtermViewHandle>();
    const onData = vi.fn();
    const onResize = vi.fn();
    const view = render(
      <XtermView
        onData={onData}
        onResize={onResize}
        ref={handle}
        resizeSignal="initial"
      />,
    );

    act(() => xtermMocks.inputHandler?.("input"));
    act(() => handle.current?.write("output"));
    act(() => handle.current?.focus());
    xtermMocks.fit.mockClear();
    onResize.mockClear();
    act(() => handle.current?.fit());

    expect(onData).toHaveBeenCalledWith("input");
    expect(xtermMocks.write).toHaveBeenCalledWith("output");
    expect(xtermMocks.focus).toHaveBeenCalledOnce();
    expect(xtermMocks.fit).toHaveBeenCalledOnce();
    expect(onResize).toHaveBeenCalledWith({ columns: 120, rows: 40 });

    view.unmount();

    expect(xtermMocks.inputDispose).toHaveBeenCalledOnce();
    expect(xtermMocks.dispose).toHaveBeenCalledOnce();
  });
});
