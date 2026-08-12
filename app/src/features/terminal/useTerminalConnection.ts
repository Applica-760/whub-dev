import { useCallback, useEffect, useRef, useState } from "react";

import type { XtermDimensions } from "../../components/XtermView";

const RECONNECT_DELAY_MS = 1_000;

type UseTerminalConnectionOptions = {
  endpoint: string;
  onConnected: () => void;
  onOutput: (data: Uint8Array) => void;
};

export function terminalUrl(path: string) {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}${path}`;
}

export function useTerminalConnection({
  endpoint,
  onConnected,
  onOutput,
}: UseTerminalConnectionOptions) {
  const socketRef = useRef<WebSocket | null>(null);
  const [error, setError] = useState<string | null>(null);

  const send = useCallback((frame: object) => {
    const socket = socketRef.current;
    if (socket?.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify(frame));
      return true;
    }
    return false;
  }, []);

  const sendInput = useCallback(
    (data: string) => {
      if (!send({ type: "input", data })) {
        setError("端末に未接続のため入力を送信できません。");
      }
    },
    [send],
  );
  const sendResize = useCallback(
    ({ columns, rows }: XtermDimensions) =>
      send({ type: "resize", columns, rows }),
    [send],
  );

  useEffect(() => {
    let disposed = false;
    let reconnectTimer: number | undefined;

    const connect = () => {
      const socket = new WebSocket(terminalUrl(endpoint));
      socket.binaryType = "arraybuffer";
      socketRef.current = socket;

      socket.addEventListener("open", () => {
        if (disposed) return;
        setError(null);
        socket.send(JSON.stringify({ type: "claim" }));
        onConnected();
      });
      socket.addEventListener("message", (event: MessageEvent) => {
        if (disposed) return;
        if (typeof event.data !== "string") {
          onOutput(new Uint8Array(event.data));
          return;
        }
        try {
          const frame = JSON.parse(event.data) as {
            detail?: unknown;
            type?: unknown;
          };
          if (frame.type === "error" && typeof frame.detail === "string") {
            setError(frame.detail);
          }
        } catch {
          setError("端末から不正な応答を受信しました。");
        }
      });
      socket.addEventListener("error", () => {
        if (!disposed) setError("端末へ接続できませんでした。");
      });
      socket.addEventListener("close", () => {
        if (disposed) return;
        if (socketRef.current === socket) socketRef.current = null;
        setError((current) => current ?? "端末接続が切断されました。");
        reconnectTimer = window.setTimeout(connect, RECONNECT_DELAY_MS);
      });
    };
    connect();

    return () => {
      disposed = true;
      if (reconnectTimer) window.clearTimeout(reconnectTimer);
      const socket = socketRef.current;
      if (socket?.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ type: "release" }));
      }
      socket?.close();
      socketRef.current = null;
    };
  }, [endpoint, onConnected, onOutput]);

  return { error, sendInput, sendResize };
}
