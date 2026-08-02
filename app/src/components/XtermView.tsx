import "@xterm/xterm/css/xterm.css";

import { FitAddon } from "@xterm/addon-fit";
import { Terminal } from "@xterm/xterm";
import type { ITerminalOptions } from "@xterm/xterm";
import {
  forwardRef,
  useCallback,
  useEffect,
  useImperativeHandle,
  useRef,
} from "react";
import type { CSSProperties } from "react";

export type XtermDimensions = {
  columns: number;
  rows: number;
};

export type XtermViewHandle = {
  fit: () => void;
  focus: () => void;
  write: (data: string) => void;
};

type XtermViewProps = {
  onData: (data: string) => void;
  onResize: (dimensions: XtermDimensions) => void;
  options?: ITerminalOptions;
  resizeSignal: string;
  style?: CSSProperties;
};

export const XtermView = forwardRef<XtermViewHandle, XtermViewProps>(
  function XtermView({ onData, onResize, options, resizeSignal, style }, ref) {
    const elementRef = useRef<HTMLDivElement>(null);
    const fitAddonRef = useRef<FitAddon | null>(null);
    const onDataRef = useRef(onData);
    const onResizeRef = useRef(onResize);
    const terminalRef = useRef<Terminal | null>(null);

    useEffect(() => {
      onDataRef.current = onData;
      onResizeRef.current = onResize;
    }, [onData, onResize]);

    const fit = useCallback(() => {
      const fitAddon = fitAddonRef.current;
      const terminal = terminalRef.current;
      if (!fitAddon || !terminal) {
        return;
      }

      fitAddon.fit();
      onResizeRef.current({ columns: terminal.cols, rows: terminal.rows });
    }, []);

    useImperativeHandle(
      ref,
      () => ({
        fit,
        focus: () => terminalRef.current?.focus(),
        write: (data) => terminalRef.current?.write(data),
      }),
      [fit],
    );

    useEffect(() => {
      const element = elementRef.current;
      if (!element) {
        return;
      }

      const terminal = new Terminal(options);
      const fitAddon = new FitAddon();
      fitAddonRef.current = fitAddon;
      terminalRef.current = terminal;
      terminal.loadAddon(fitAddon);
      terminal.open(element);

      const input = terminal.onData((data) => onDataRef.current(data));
      const resizeObserver = new ResizeObserver(fit);
      resizeObserver.observe(element);

      return () => {
        input.dispose();
        resizeObserver.disconnect();
        terminal.dispose();
        fitAddonRef.current = null;
        terminalRef.current = null;
      };
    }, [fit, options]);

    useEffect(() => {
      const animationFrame = requestAnimationFrame(fit);
      return () => cancelAnimationFrame(animationFrame);
    }, [fit, resizeSignal]);

    return <div ref={elementRef} style={style} />;
  },
);
