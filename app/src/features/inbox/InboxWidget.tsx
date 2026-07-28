import { Text } from "@mantine/core";
import { WidgetFrame } from "../../components/WidgetFrame";

import { InboxForm } from "./InboxForm";

export function InboxWidget() {
  return (
    <WidgetFrame
      title={
        <Text c="dimmed" fw={600} size="sm">
          Inbox
        </Text>
      }
    >
      <InboxForm />
    </WidgetFrame>
  );
}
