import { Alert, Badge, Button, Stack, Table, Text } from "@mantine/core";

import { WidgetFrame } from "../../components/WidgetFrame";
import { useResourceStatus } from "./useResourceStatus";

function statusColor(status: string): string {
  if (status === "ok") {
    return "green";
  }
  if (status === "stale" || status === "unmounted") {
    return "yellow";
  }
  return "red";
}

function StatusValue({ value }: { value: string }) {
  if (value === "-") {
    return value;
  }
  return (
    <Badge color={statusColor(value)} variant="light">
      {value}
    </Badge>
  );
}

export function ResourceStatusWidget() {
  const { resources, loading, error, updatedAt, refresh } = useResourceStatus();

  return (
    <WidgetFrame
      action={
        <Button
          loading={loading}
          onClick={() => void refresh()}
          size="xs"
          variant="light"
        >
          更新
        </Button>
      }
      title={
        <Stack gap={0}>
          <Text c="dimmed" fw={600} size="sm">
            Status
          </Text>
          <Text c="dimmed" size="xs">
            最終更新: {updatedAt ? updatedAt.toLocaleString("ja-JP") : "未取得"}
          </Text>
        </Stack>
      }
    >
      {error && (
        <Alert color="red" title="Statusを取得できませんでした">
          {error}
        </Alert>
      )}

      {loading && resources.length === 0 ? (
        <Text c="dimmed" p="md">
          Statusを読み込んでいます…
        </Text>
      ) : (
        <Table highlightOnHover style={{ tableLayout: "fixed" }}>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Project</Table.Th>
              <Table.Th>State</Table.Th>
              <Table.Th>Type</Table.Th>
              <Table.Th>Mount</Table.Th>
              <Table.Th>Tmux</Table.Th>
              <Table.Th>Git</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {resources.map((resource) => (
              <Table.Tr key={resource.project}>
                <Table.Td style={{ overflowWrap: "anywhere" }}>
                  {resource.project}
                </Table.Td>
                <Table.Td>
                  <StatusValue value={resource.state} />
                </Table.Td>
                <Table.Td>{resource.type}</Table.Td>
                <Table.Td>
                  <StatusValue value={resource.mount} />
                </Table.Td>
                <Table.Td>
                  <StatusValue value={resource.tmux} />
                </Table.Td>
                <Table.Td>{resource.git}</Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      )}

      {!loading && resources.length === 0 && !error && (
        <Text c="dimmed" p="md">
          表示対象のresourceはありません。
        </Text>
      )}
    </WidgetFrame>
  );
}
