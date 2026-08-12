import { Paper, Stack } from "@mantine/core";
import type { ReactNode } from "react";

type TerminalWidgetFrameProps = {
  children: ReactNode;
};

export function TerminalWidgetFrame({ children }: TerminalWidgetFrameProps) {
  return (
    <Stack h="100%" style={{ minHeight: 0 }}>
      <Paper
        className="whub-box"
        radius="md"
        shadow="xs"
        style={{ flex: "1 1 0", minHeight: 0 }}
        withBorder
      >
        {children}
      </Paper>
    </Stack>
  );
}
