import { Alert, Badge, Button, Table, Text } from "@mantine/core";

import { PageFrame } from "../../components/PageFrame";
import { WidgetFrame } from "../../components/WidgetFrame";
import { useWorktrees } from "./useWorktrees";

function value(value: string | null) {
  return value ?? "-";
}

export function WorktreesPage() {
  const { error, loading, refresh, worktrees } = useWorktrees();

  return (
    <PageFrame>
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
        title="Worktrees"
      >
        {error && <Alert color="red">{error}</Alert>}
        {loading && worktrees.length === 0 ? (
          <Text c="dimmed" p="md">
            読み込んでいます…
          </Text>
        ) : (
          <Table highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Parent</Table.Th>
                <Table.Th>Task</Table.Th>
                <Table.Th>Branch</Table.Th>
                <Table.Th>Path</Table.Th>
                <Table.Th>State</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {worktrees.map((worktree) => (
                <Table.Tr
                  key={`${worktree.parent_project}/${worktree.task_id}/${worktree.workspace_path}`}
                >
                  <Table.Td>{value(worktree.parent_project)}</Table.Td>
                  <Table.Td>{value(worktree.task_id)}</Table.Td>
                  <Table.Td>{value(worktree.branch)}</Table.Td>
                  <Table.Td>{value(worktree.workspace_path)}</Table.Td>
                  <Table.Td>
                    <Badge
                      color={worktree.diagnostics.length ? "red" : "green"}
                      variant="light"
                    >
                      {worktree.diagnostics.length
                        ? worktree.diagnostics.join("; ")
                        : "ok"}
                    </Badge>
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        )}
        {!loading && worktrees.length === 0 && !error && (
          <Text c="dimmed" p="md">
            登録済みworktreeはありません。
          </Text>
        )}
      </WidgetFrame>
    </PageFrame>
  );
}
