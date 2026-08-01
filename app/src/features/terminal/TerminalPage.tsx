import { Alert, Select, Text } from "@mantine/core";
import { useEffect, useMemo, useState } from "react";

import { WidgetFrame } from "../../components/WidgetFrame";
import {
  OverviewColumn,
  OverviewFrame,
  OverviewWide,
} from "../overview/OverviewFrame";
import type { WorktreeItem } from "../worktrees/api";
import { useWorktrees } from "../worktrees/useWorktrees";

function terminalWorktrees(worktrees: WorktreeItem[]) {
  return worktrees.filter(
    (worktree) => worktree.parent_project !== null && worktree.task_id !== null,
  );
}

function worktreeValue(worktree: WorktreeItem) {
  return `${worktree.parent_project}/${worktree.task_id}`;
}

export function TerminalPage() {
  const { error, loading, worktrees } = useWorktrees();
  const terminals = useMemo(() => terminalWorktrees(worktrees), [worktrees]);
  const [selectedTerminal, setSelectedTerminal] = useState<string | null>(null);

  useEffect(() => {
    setSelectedTerminal((current) => {
      if (
        current &&
        terminals.some((worktree) => worktreeValue(worktree) === current)
      ) {
        return current;
      }
      return terminals[0] ? worktreeValue(terminals[0]) : null;
    });
  }, [terminals]);

  return (
    <OverviewFrame collapsed={{ left: false, right: false }}>
      <OverviewWide>
        <WidgetFrame title="Terminal">
          <Select
            aria-label="Terminalのworktreeを選択"
            data={terminals.map((worktree) => ({
              label: `${worktree.parent_project} / ${worktree.task_id}`,
              value: worktreeValue(worktree),
            }))}
            disabled={loading || terminals.length === 0}
            onChange={setSelectedTerminal}
            p="md"
            placeholder={
              loading ? "worktreeを読み込んでいます…" : "worktreeがありません"
            }
            value={selectedTerminal}
          />
          {error && (
            <Alert color="red" m="md">
              {error}
            </Alert>
          )}
        </WidgetFrame>
      </OverviewWide>
      <OverviewColumn>
        <WidgetFrame title="Terminal">
          <Text c="dimmed" p="md">
            {selectedTerminal
              ? "端末を接続する準備ができました。"
              : "表示できる端末はありません。"}
          </Text>
        </WidgetFrame>
      </OverviewColumn>
      <OverviewColumn>
        <WidgetFrame title="Session">
          <Text c="dimmed" p="md">
            Session情報は後続のPhaseで追加します。
          </Text>
        </WidgetFrame>
      </OverviewColumn>
      <OverviewColumn>
        <WidgetFrame title="Activity">
          <Text c="dimmed" p="md">
            Activity情報は後続のPhaseで追加します。
          </Text>
        </WidgetFrame>
      </OverviewColumn>
    </OverviewFrame>
  );
}
