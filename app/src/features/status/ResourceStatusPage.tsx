import {
  Alert,
  Badge,
  Button,
  Group,
  Paper,
  Stack,
  Table,
  Text,
  Title,
} from '@mantine/core';

import { PageFrame } from '../../components/PageFrame';
import { useResourceStatus } from './useResourceStatus';

function statusColor(status: string): string {
  if (status === 'ok') {
    return 'green';
  }
  if (status === 'stale' || status === 'unmounted') {
    return 'yellow';
  }
  return 'red';
}

function StatusValue({ value }: { value: string }) {
  if (value === '-') {
    return value;
  }
  return (
    <Badge color={statusColor(value)} variant="light">
      {value}
    </Badge>
  );
}

export function ResourceStatusPage() {
  const { resources, loading, error, updatedAt, refresh } = useResourceStatus();

  return (
    <PageFrame>
      <Stack gap="md">
        <Group justify="space-between">
          <div>
            <Title order={2}>Status</Title>
            <Text c="dimmed" size="sm">
              最終更新: {updatedAt ? updatedAt.toLocaleString('ja-JP') : '未取得'}
            </Text>
          </div>
          <Button loading={loading} onClick={() => void refresh()} variant="light">
            更新
          </Button>
        </Group>

        {error && <Alert color="red" title="Statusを取得できませんでした">{error}</Alert>}

        {loading && resources.length === 0 ? (
          <Text c="dimmed">Statusを読み込んでいます…</Text>
        ) : (
          <Paper radius="md" shadow="xs" withBorder>
            <Table.ScrollContainer minWidth={720}>
              <Table highlightOnHover>
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
                      <Table.Td>{resource.project}</Table.Td>
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
            </Table.ScrollContainer>
          </Paper>
        )}

        {!loading && resources.length === 0 && !error && (
          <Text c="dimmed">表示対象のresourceはありません。</Text>
        )}
      </Stack>
    </PageFrame>
  );
}
