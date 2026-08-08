import { Alert, Text } from "@mantine/core";
import { useCallback, useMemo, useRef } from "react";

import { XtermView } from "../../components/XtermView";
import type { XtermViewHandle } from "../../components/XtermView";
import { useTerminalConnection } from "./useTerminalConnection";

type TerminalWidgetProps = {
  resizeSignal: string;
} & (
  | { endpoint: string; label: string; project?: never; taskId?: never }
  | { endpoint?: never; label?: never; project: string; taskId: string }
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
  endpoint,
  label,
  project,
  resizeSignal,
  taskId,
}: TerminalWidgetProps) {
  const xtermRef = useRef<XtermViewHandle>(null);
  const decoderRef = useRef(new TextDecoder());
  const terminalOptions = useMemo(
    () => (taskId ? { macOptionClickForcesSelection: true } : undefined),
    [taskId],
  );
  const handleConnected = useCallback(() => {
    xtermRef.current?.fit(true);
    xtermRef.current?.focus();
  }, []);
  const handleOutput = useCallback((data: Uint8Array) => {
    xtermRef.current?.write(decoderRef.current.decode(data, { stream: true }));
  }, []);
  const { error, sendInput, sendResize } = useTerminalConnection({
    endpoint:
      endpoint ??
      `/api/terminals/${encodeURIComponent(project)}/${encodeURIComponent(taskId)}`,
    onConnected: handleConnected,
    onOutput: handleOutput,
  });

  return (
    <>
      {error && (
        <Alert color="red" m="md">
          {error}
        </Alert>
      )}
      <XtermView
        onData={sendInput}
        onLink={openWebLink}
        onResize={sendResize}
        options={terminalOptions}
        ref={xtermRef}
        resizeSignal={resizeSignal}
      />
      <Text c="dimmed" px="md" pb="md" size="sm">
        {label ?? `${project} / ${taskId}`}
      </Text>
    </>
  );
}
