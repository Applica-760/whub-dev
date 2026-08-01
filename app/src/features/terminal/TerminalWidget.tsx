import "@xterm/xterm/css/xterm.css";

import { Alert, Text } from "@mantine/core";
import { FitAddon } from "@xterm/addon-fit";
import { Terminal } from "@xterm/xterm";
import { useEffect, useRef, useState } from "react";

type TerminalWidgetProps = {
  project: string;
  taskId: string;
};

function terminalUrl(project: string, taskId: string) {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}/api/terminals/${encodeURIComponent(project)}/${encodeURIComponent(taskId)}`;
}

export function TerminalWidget({ project, taskId }: TerminalWidgetProps) {
  const elementRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const element = elementRef.current;
    if (!element) {
      return;
    }

    const terminal = new Terminal({ cursorBlink: true, fontSize: 14 });
    const fitAddon = new FitAddon();
    const socket = new WebSocket(terminalUrl(project, taskId));
    terminal.loadAddon(fitAddon);
    terminal.open(element);

    const resize = () => {
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
    };
    const resizeObserver = new ResizeObserver(resize);
    const input = terminal.onData((data) => socket.send(data));

    socket.addEventListener("open", () => {
      socket.send(JSON.stringify({ type: "claim" }));
      resize();
      terminal.focus();
    });
    socket.addEventListener("message", (event) => terminal.write(event.data));
    socket.addEventListener("error", () => {
      setError("端末へ接続できませんでした。");
    });
    socket.addEventListener("close", () => {
      setError((current) => current ?? "端末接続が切断されました。");
    });
    resizeObserver.observe(element);

    return () => {
      input.dispose();
      resizeObserver.disconnect();
      socket.close();
      terminal.dispose();
    };
  }, [project, taskId]);

  return (
    <>
      {error && (
        <Alert color="red" m="md">
          {error}
        </Alert>
      )}
      <div ref={elementRef} style={{ height: "32rem", padding: "0.5rem" }} />
      <Text c="dimmed" px="md" pb="md" size="sm">
        {project} / {taskId}
      </Text>
    </>
  );
}
