import { Anchor, Stack, Text } from "@mantine/core";
import { useEffect, useState } from "react";

import { requestJson } from "../../api/client";
import { PageFrame } from "../../components/PageFrame";
import { listProjects } from "../projects/api";

type Issue = { number: number; title: string; url: string };

export function TasksPage() {
  const [issues, setIssues] = useState<{ project: string; issue: Issue }[]>([]);

  useEffect(() => {
    void listProjects()
      .then((projects) => Promise.allSettled(projects.map(async (project) =>
        (await requestJson<Issue[]>(`/api/issues/${encodeURIComponent(project)}`))
          .map((issue) => ({ project, issue })),
      )))
      .then((listed) => setIssues(listed.flatMap((result) =>
        result.status === "fulfilled" ? result.value : [],
      )))
      .catch(() => setIssues([]));
  }, []);

  return (
    <PageFrame>
      <Stack gap="md">
        {issues.length ? issues.map(({ project, issue }) => (
          <Anchor href={issue.url} key={`${project}/${issue.number}`} target="_blank">
            {project} #{issue.number} {issue.title}
          </Anchor>
        )) : <Text c="dimmed">Open Issueはありません。</Text>}
      </Stack>
    </PageFrame>
  );
}
