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
  linkHandler: undefined as
    ((event: MouseEvent, uri: string) => void) | undefined,
  loadAddon: vi.fn(),
  open: vi.fn(),
  options: undefined as unknown,
  write: vi.fn(),
}));

vi.mock("@xterm/xterm", () => ({
  Terminal: class {
    cols = 120;
    rows = 40;

    constructor(options: unknown) {
      xtermMocks.options = options;
    }

    dispose = xtermMocks.dispose;
    focus = xtermMocks.focus;
    loadAddon = xtermMocks.loadAddon;
    open = xtermMocks.open;
    write = xtermMocks.write;

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

vi.mock("@xterm/addon-web-links", () => ({
  WebLinksAddon: class {
    constructor(handler: (event: MouseEvent, uri: string) => void) {
      xtermMocks.linkHandler = handler;
    }
  },
}));

beforeEach(() => {
  xtermMocks.inputHandler = undefined;
  xtermMocks.linkHandler = undefined;
  xtermMocks.options = undefined;
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
  vi.stubGlobal(
    "getComputedStyle",
    vi.fn(
      () =>
        ({
          getPropertyValue: (name: string) =>
            ({
              "--xterm-font-family":
                '"SFMono-Regular", "SF Mono", "Noto Sans Mono CJK JP", "Noto Sans Mono", Menlo, Monaco, Consolas, monospace',
              "--xterm-font-size": "15",
              "--xterm-font-weight": "400",
              "--xterm-font-weight-bold": "600",
              "--xterm-line-height": "1.25",
              "--xterm-letter-spacing": "0",
              "--xterm-minimum-contrast": "4.5",
              "--xterm-background": "#0d1117",
              "--xterm-foreground": "#c9d1d9",
              "--xterm-red": "#ff7b72",
              "--xterm-green": "#7ee787",
              "--xterm-bright-yellow": "#f2cc60",
              "--xterm-bright-blue": "#79c0ff",
            })[name] ?? "",
        }) as CSSStyleDeclaration,
    ),
  );
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("XtermView", () => {
  it("xtermの入出力・fit・focus・破棄をcomponent内で管理する", () => {
    const handle = createRef<XtermViewHandle>();
    const onData = vi.fn();
    const onLink = vi.fn();
    const onResize = vi.fn();
    const view = render(
      <XtermView
        onData={onData}
        onLink={onLink}
        onResize={onResize}
        ref={handle}
        resizeSignal="initial"
      />,
    );

    act(() => xtermMocks.inputHandler?.("input"));
    const linkEvent = new MouseEvent("click", { metaKey: true });
    act(() => xtermMocks.linkHandler?.(linkEvent, "https://example.com"));
    act(() => handle.current?.write("output"));
    act(() => handle.current?.focus());
    xtermMocks.fit.mockClear();
    onResize.mockClear();
    act(() => handle.current?.fit());

    expect(onData).toHaveBeenCalledWith("input");
    expect(onLink).toHaveBeenCalledWith(linkEvent, "https://example.com");
    expect(xtermMocks.loadAddon).toHaveBeenCalledTimes(2);
    expect(xtermMocks.options).toMatchObject({
      cursorBlink: false,
      fontFamily:
        '"SFMono-Regular", "SF Mono", "Noto Sans Mono CJK JP", "Noto Sans Mono", Menlo, Monaco, Consolas, monospace',
      fontSize: 15,
      fontWeight: 400,
      fontWeightBold: 600,
      lineHeight: 1.25,
      letterSpacing: 0,
      minimumContrastRatio: 4.5,
      theme: {
        background: "#0d1117",
        foreground: "#c9d1d9",
        red: "#ff7b72",
        green: "#7ee787",
        brightYellow: "#f2cc60",
        brightBlue: "#79c0ff",
      },
    });
    expect(xtermMocks.write).toHaveBeenCalledWith("output");
    expect(xtermMocks.focus).toHaveBeenCalledOnce();
    expect(xtermMocks.fit).toHaveBeenCalledOnce();
    expect(onResize).not.toHaveBeenCalled();

    view.unmount();

    expect(xtermMocks.inputDispose).toHaveBeenCalledOnce();
    expect(xtermMocks.dispose).toHaveBeenCalledOnce();
  });
});
