import "@xterm/xterm/css/xterm.css";

import { Alert, Text } from "@mantine/core";
import { FitAddon } from "@xterm/addon-fit";
import { Terminal } from "@xterm/xterm";
import { useCallback, useEffect, useRef, useState } from "react";

type TerminalWidgetProps = {
  project: string;
  resizeSignal: string;
  taskId: string;
};

function terminalUrl(project: string, taskId: string) {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}/api/terminals/${encodeURIComponent(project)}/${encodeURIComponent(taskId)}`;
}

export function TerminalWidget({
  project,
  resizeSignal,
  taskId,
}: TerminalWidgetProps) {
  const elementRef = useRef<HTMLDivElement>(null);
  const fitAddonRef = useRef<FitAddon | null>(null);
  const socketRef = useRef<WebSocket | null>(null);
  const terminalRef = useRef<Terminal | null>(null);
  const [error, setError] = useState<string | null>(null);

  const resize = useCallback(() => {
    const fitAddon = fitAddonRef.current;
    const socket = socketRef.current;
    const terminal = terminalRef.current;
    if (!fitAddon || !socket || !terminal) {
      return;
    }

    fitAddon.fit();
    if (socket.readyState === WebSocket.OPEN) {
      socket.send(
        JSON.stringify({
          type: "resize",
          columns: terminal.cols,
          rows: terminal.rows,
        }),
      );
    }
  }, []);

  useEffect(() => {
    const element = elementRef.current;
    if (!element) {
      return;
    }

    const terminal = new Terminal({ cursorBlink: true, fontSize: 14 });
    const fitAddon = new FitAddon();
    const socket = new WebSocket(terminalUrl(project, taskId));
    let disposed = false;
    fitAddonRef.current = fitAddon;
    socketRef.current = socket;
    terminalRef.current = terminal;
    setError(null);
    terminal.loadAddon(fitAddon);
    terminal.open(element);

    const resizeObserver = new ResizeObserver(resize);
    const input = terminal.onData((data) => {
      if (socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ type: "input", data }));
      }
    });

    socket.addEventListener("open", () => {
      socket.send(JSON.stringify({ type: "claim" }));
      resize();
      terminal.focus();
    });
    socket.addEventListener("message", (event) => terminal.write(event.data));
    socket.addEventListener("error", () => {
      if (!disposed) {
        setError("端末へ接続できませんでした。");
      }
    });
    socket.addEventListener("close", () => {
      if (!disposed) {
        setError((current) => current ?? "端末接続が切断されました。");
      }
    });
    resizeObserver.observe(element);

    return () => {
      disposed = true;
      input.dispose();
      resizeObserver.disconnect();
      if (socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ type: "release" }));
      }
      socket.close();
      terminal.dispose();
      fitAddonRef.current = null;
      socketRef.current = null;
      terminalRef.current = null;
    };
  }, [project, resize, taskId]);

  useEffect(() => {
    const animationFrame = requestAnimationFrame(resize);
    return () => cancelAnimationFrame(animationFrame);
  }, [resize, resizeSignal]);

  return (
    <>
      {error && (
        <Alert color="red" m="md">
          {error}
        </Alert>
      )}
      <div ref={elementRef} style={{ height: "64rem", padding: "0.5rem" }} />
      <Text c="dimmed" px="md" pb="md" size="sm">
        {project} / {taskId}
      </Text>
    </>
  );
}
