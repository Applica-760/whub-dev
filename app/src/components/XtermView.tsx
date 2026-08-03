import "@xterm/xterm/css/xterm.css";
import "./XtermView.css";

import { FitAddon } from "@xterm/addon-fit";
import { WebLinksAddon } from "@xterm/addon-web-links";
import { Terminal } from "@xterm/xterm";
import type { ITheme, ITerminalOptions } from "@xterm/xterm";
import {
  forwardRef,
  useCallback,
  useEffect,
  useImperativeHandle,
  useRef,
} from "react";

const THEME_VARIABLES = {
  background: "--xterm-background",
  foreground: "--xterm-foreground",
  cursor: "--xterm-cursor",
  cursorAccent: "--xterm-cursor-accent",
  selectionBackground: "--xterm-selection",
  selectionInactiveBackground: "--xterm-selection-inactive",
  black: "--xterm-black",
  red: "--xterm-red",
  green: "--xterm-green",
  yellow: "--xterm-yellow",
  blue: "--xterm-blue",
  magenta: "--xterm-magenta",
  cyan: "--xterm-cyan",
  white: "--xterm-white",
  brightBlack: "--xterm-bright-black",
  brightRed: "--xterm-bright-red",
  brightGreen: "--xterm-bright-green",
  brightYellow: "--xterm-bright-yellow",
  brightBlue: "--xterm-bright-blue",
  brightMagenta: "--xterm-bright-magenta",
  brightCyan: "--xterm-bright-cyan",
  brightWhite: "--xterm-bright-white",
} satisfies Partial<Record<keyof ITheme, string>>;

function cssValue(styles: CSSStyleDeclaration, name: string) {
  return styles.getPropertyValue(name).trim();
}

function cssNumber(styles: CSSStyleDeclaration, name: string) {
  const value = Number.parseFloat(cssValue(styles, name));
  return Number.isFinite(value) ? value : undefined;
}

function resolveOptions(
  element: HTMLElement,
  options?: ITerminalOptions,
): ITerminalOptions {
  const styles = getComputedStyle(element);
  const theme = Object.fromEntries(
    Object.entries(THEME_VARIABLES)
      .map(([name, variable]) => [name, cssValue(styles, variable)])
      .filter(([, value]) => value),
  ) as ITheme;
  const resolved: ITerminalOptions = {
    cursorBlink: true,
    ...options,
    theme: { ...options?.theme, ...theme },
  };
  const fontFamily = cssValue(styles, "--xterm-font-family");
  const fontSize = cssNumber(styles, "--xterm-font-size");
  const lineHeight = cssNumber(styles, "--xterm-line-height");
  const minimumContrastRatio = cssNumber(styles, "--xterm-minimum-contrast");

  if (fontFamily) resolved.fontFamily = fontFamily;
  if (fontSize !== undefined) resolved.fontSize = fontSize;
  if (lineHeight !== undefined) resolved.lineHeight = lineHeight;
  if (minimumContrastRatio !== undefined) {
    resolved.minimumContrastRatio = minimumContrastRatio;
  }
  return resolved;
}

export type XtermDimensions = {
  columns: number;
  rows: number;
};

export type XtermViewHandle = {
  fit: (forceResize?: boolean) => void;
  focus: () => void;
  write: (data: string) => void;
};

type XtermViewProps = {
  onData: (data: string) => void;
  onLink?: (event: MouseEvent, uri: string) => void;
  onResize: (dimensions: XtermDimensions) => void;
  options?: ITerminalOptions;
  resizeSignal: string;
};

export const XtermView = forwardRef<XtermViewHandle, XtermViewProps>(
  function XtermView({ onData, onLink, onResize, options, resizeSignal }, ref) {
    const elementRef = useRef<HTMLDivElement>(null);
    const fitAddonRef = useRef<FitAddon | null>(null);
    const onDataRef = useRef(onData);
    const onLinkRef = useRef(onLink);
    const onResizeRef = useRef(onResize);
    const lastDimensionsRef = useRef<XtermDimensions | null>(null);
    const terminalRef = useRef<Terminal | null>(null);
    const linksEnabled = onLink !== undefined;

    useEffect(() => {
      onDataRef.current = onData;
      onLinkRef.current = onLink;
      onResizeRef.current = onResize;
    }, [onData, onLink, onResize]);

    const fit = useCallback((forceResize = false) => {
      const fitAddon = fitAddonRef.current;
      const terminal = terminalRef.current;
      if (!fitAddon || !terminal) {
        return;
      }

      fitAddon.fit();
      const dimensions = { columns: terminal.cols, rows: terminal.rows };
      if (
        !forceResize &&
        lastDimensionsRef.current?.columns === dimensions.columns &&
        lastDimensionsRef.current.rows === dimensions.rows
      ) {
        return;
      }
      lastDimensionsRef.current = dimensions;
      onResizeRef.current(dimensions);
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

      const terminal = new Terminal(resolveOptions(element, options));
      const fitAddon = new FitAddon();
      fitAddonRef.current = fitAddon;
      terminalRef.current = terminal;
      terminal.loadAddon(fitAddon);
      if (linksEnabled) {
        terminal.loadAddon(
          new WebLinksAddon((event, uri) => onLinkRef.current?.(event, uri)),
        );
      }
      terminal.open(element);

      const input = terminal.onData((data) => onDataRef.current(data));
      const resizeObserver = new ResizeObserver(() => fit());
      resizeObserver.observe(element);

      return () => {
        input.dispose();
        resizeObserver.disconnect();
        terminal.dispose();
        fitAddonRef.current = null;
        terminalRef.current = null;
      };
    }, [fit, linksEnabled, options]);

    useEffect(() => {
      const animationFrame = requestAnimationFrame(() => fit());
      return () => cancelAnimationFrame(animationFrame);
    }, [fit, resizeSignal]);

    return <div className="xterm-view" ref={elementRef} />;
  },
);
