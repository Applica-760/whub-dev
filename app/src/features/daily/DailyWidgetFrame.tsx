import { Box, Button, Group, Text } from "@mantine/core";
import { useState } from "react";

import { WidgetFrame } from "../../components/WidgetFrame";
import { InboxForm } from "../inbox/InboxForm";

import { DailyForm } from "./DailyForm";

type Mode = "inbox" | "daily";

export function DailyWidgetFrame() {
  const [mode, setMode] = useState<Mode>("inbox");

  return (
    <WidgetFrame
      action={
        <Group gap={4}>
          <Button
            aria-pressed={mode === "inbox"}
            onClick={() => setMode("inbox")}
            size="compact-xs"
            variant={mode === "inbox" ? "light" : "subtle"}
          >
            Inbox
          </Button>
          <Button
            aria-pressed={mode === "daily"}
            onClick={() => setMode("daily")}
            size="compact-xs"
            variant={mode === "daily" ? "light" : "subtle"}
          >
            Daily
          </Button>
        </Group>
      }
      title={
        <Text c="dimmed" fw={600} size="sm">
          {mode === "inbox" ? "Inbox" : "Daily"}
        </Text>
      }
    >
      <Box hidden={mode !== "inbox"}>
        <InboxForm />
      </Box>
      <Box hidden={mode !== "daily"}>
        <DailyForm />
      </Box>
    </WidgetFrame>
  );
}
