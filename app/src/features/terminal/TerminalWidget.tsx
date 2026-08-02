import { Alert, Text } from "@mantine/core";
import type { ITerminalOptions } from "@xterm/xterm";
import { useCallback, useRef } from "react";

import { XtermView } from "../../components/XtermView";
import type { XtermViewHandle } from "../../components/XtermView";
import { useTerminalConnection } from "./useTerminalConnection";

type TerminalWidgetProps = {
  project: string;
  resizeSignal: string;
  taskId: string;
};

const XTERM_OPTIONS: ITerminalOptions = { cursorBlink: true, fontSize: 14 };
const XTERM_STYLE = { height: "64rem", padding: "0.5rem" };

export function TerminalWidget({
  project,
  resizeSignal,
  taskId,
}: TerminalWidgetProps) {
  const xtermRef = useRef<XtermViewHandle>(null);
  const handleConnected = useCallback(() => {
    xtermRef.current?.fit();
    xtermRef.current?.focus();
  }, []);
  const handleOutput = useCallback((data: string) => {
    xtermRef.current?.write(data);
  }, []);
  const { error, sendInput, sendResize } = useTerminalConnection({
    onConnected: handleConnected,
    onOutput: handleOutput,
    project,
    taskId,
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
        onResize={sendResize}
        options={XTERM_OPTIONS}
        ref={xtermRef}
        resizeSignal={resizeSignal}
        style={XTERM_STYLE}
      />
      <Text c="dimmed" px="md" pb="md" size="sm">
        {project} / {taskId}
      </Text>
    </>
  );
}
