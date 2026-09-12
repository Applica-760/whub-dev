import { Alert } from "@mantine/core";
import { useCallback, useEffect, useMemo, useRef } from "react";

import { XtermView } from "../../components/XtermView";
import type { XtermViewHandle } from "../../components/XtermView";
import { useTerminalConnection } from "./useTerminalConnection";

type TerminalWidgetProps = {
  active?: boolean;
  resizeSignal: string;
} & (
  | { endpoint: string; project?: never; issueNumber?: never }
  | { endpoint?: never; project: string; issueNumber: number }
);

function openWebLink(event: MouseEvent, uri: string) {
  if (!event.metaKey && !event.ctrlKey) {
    return;
  }

  try {
    const url = new URL(uri);
    if (url.protocol === "http:" || url.protocol === "https:") {
      window.open(url.href, "_blank", "noopener,noreferrer");
    }
  } catch {
    return;
  }
}

export function TerminalWidget({
  active = true,
  endpoint,
  project,
  resizeSignal,
  issueNumber,
}: TerminalWidgetProps) {
  const activeRef = useRef(active);
  const previousActiveRef = useRef(active);
  const xtermRef = useRef<XtermViewHandle>(null);
  const decoderRef = useRef(new TextDecoder());
  const terminalOptions = useMemo(
    () => ({ macOptionClickForcesSelection: true }),
    [],
  );
  activeRef.current = active;
  const handleConnected = useCallback(() => {
    if (!activeRef.current) return;
    xtermRef.current?.fit(true);
    xtermRef.current?.focus();
  }, []);
  const handleOutput = useCallback((data: Uint8Array) => {
    xtermRef.current?.write(decoderRef.current.decode(data, { stream: true }));
  }, []);
  const { error, sendInput, sendResize } = useTerminalConnection({
    endpoint:
      endpoint ??
      `/api/terminals/${encodeURIComponent(project)}/${issueNumber}`,
    onConnected: handleConnected,
    onOutput: handleOutput,
  });
  useEffect(() => {
    if (active && !previousActiveRef.current) xtermRef.current?.focus();
    previousActiveRef.current = active;
  }, [active]);

  return (
    <div className="terminal-widget">
      {error && (
        <Alert color="red" m="md">
          {error}
        </Alert>
      )}
      <XtermView
        active={active}
        onData={sendInput}
        onLink={openWebLink}
        onResize={sendResize}
        options={terminalOptions}
        ref={xtermRef}
        resizeSignal={resizeSignal}
      />
    </div>
  );
}
