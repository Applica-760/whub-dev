import { Anchor, Text } from "@mantine/core";
import { useEffect, useState } from "react";

import { requestJson } from "../../../api/client";

type TerminalTaskPanelProps = {
  collapsed: boolean;
  project: string | null;
};

export function TerminalTaskPanel({
  collapsed,
  project,
}: TerminalTaskPanelProps) {
  const [issues, setIssues] = useState<
    { number: number; title: string; url: string }[]
  >([]);
  useEffect(() => {
    if (!project) return void setIssues([]);
    void requestJson<typeof issues>(
      `/api/issues/${encodeURIComponent(project)}`,
    ).then(setIssues, () => setIssues([]));
  }, [project]);
  return (
    <aside
      className="terminal-task-panel"
      data-collapsed={collapsed || undefined}
    >
      {issues.length ? issues.map((issue) => (
        <Anchor href={issue.url} key={issue.number} target="_blank">
          #{issue.number} {issue.title}
        </Anchor>
      )) : <Text c="dimmed" p="md">Open Issueはありません。</Text>}
    </aside>
  );
}
