import { Group, Paper, Stack } from "@mantine/core";
import type { ReactNode } from "react";

type WidgetFrameProps = {
  title?: ReactNode;
  action?: ReactNode;
  children: ReactNode;
};

export function WidgetFrame({ title, action, children }: WidgetFrameProps) {
  return (
    <Stack gap={2} h="100%" style={{ minHeight: 0 }}>
      {(title || action) && (
        <Group justify="space-between" px="xs" wrap="nowrap">
          {title}
          {action}
        </Group>
      )}
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
