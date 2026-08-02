import { useCallback, useEffect, useRef, useState } from "react";

import type { XtermDimensions } from "../../components/XtermView";

type UseTerminalConnectionOptions = {
  onConnected: () => void;
  onOutput: (data: string) => void;
  project: string;
  taskId: string;
};

function terminalUrl(project: string, taskId: string) {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}/api/terminals/${encodeURIComponent(project)}/${encodeURIComponent(taskId)}`;
}

export function useTerminalConnection({
  onConnected,
  onOutput,
  project,
  taskId,
}: UseTerminalConnectionOptions) {
  const socketRef = useRef<WebSocket | null>(null);
  const [error, setError] = useState<string | null>(null);

  const send = useCallback((frame: object) => {
    const socket = socketRef.current;
    if (socket?.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify(frame));
    }
  }, []);

  const sendInput = useCallback(
    (data: string) => send({ type: "input", data }),
    [send],
  );
  const sendResize = useCallback(
    ({ columns, rows }: XtermDimensions) =>
      send({ type: "resize", columns, rows }),
    [send],
  );

  useEffect(() => {
    const socket = new WebSocket(terminalUrl(project, taskId));
    let disposed = false;
    socketRef.current = socket;
    setError(null);

    socket.addEventListener("open", () => {
      if (disposed) {
        return;
      }
      socket.send(JSON.stringify({ type: "claim" }));
      onConnected();
    });
    socket.addEventListener("message", (event) => {
      if (!disposed) {
        onOutput(event.data);
      }
    });
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

    return () => {
      disposed = true;
      if (socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ type: "release" }));
      }
      socket.close();
      if (socketRef.current === socket) {
        socketRef.current = null;
      }
    };
  }, [onConnected, onOutput, project, taskId]);

  return { error, sendInput, sendResize };
}
