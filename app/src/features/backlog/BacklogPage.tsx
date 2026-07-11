import {
  Alert,
  Button,
  Divider,
  Group,
  Paper,
  Stack,
  Text,
  TextInput,
  Title,
} from '@mantine/core';
import { useCallback, useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import ReactMarkdown from 'react-markdown';

import {
  type BacklogResponse,
  type ProjectsResponse,
  requestJson,
} from '../../api/client';
import { GroupedListRow, GroupedListSection } from '../../components/GroupedList';
import { PageFrame } from '../../components/PageFrame';

const APPENDED_START = '<!-- hub:backlog:appended:start -->';
const APPENDED_END = '<!-- hub:backlog:appended:end -->';

export function BacklogPage() {
  const [projects, setProjects] = useState<string[]>([]);
  const [selectedProject, setSelectedProject] = useState<string | null>(null);
  const [projectsLoading, setProjectsLoading] = useState(true);
  const [projectsError, setProjectsError] = useState<string | null>(null);
  const [content, setContent] = useState('');
  const [backlogLoading, setBacklogLoading] = useState(false);
  const [backlogError, setBacklogError] = useState<string | null>(null);
  const [memo, setMemo] = useState('');
  const [appending, setAppending] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function loadProjects() {
      setProjectsLoading(true);
      setProjectsError(null);
      try {
        const response = await requestJson<ProjectsResponse>('/api/projects');
        if (cancelled) {
          return;
        }
        setProjects(response.projects);
        setSelectedProject((current) => (
          current && response.projects.includes(current)
            ? current
            : (response.projects[0] ?? null)
        ));
      } catch (requestError) {
        if (!cancelled) {
          setProjectsError(errorMessage(requestError));
        }
      } finally {
        if (!cancelled) {
          setProjectsLoading(false);
        }
      }
    }

    void loadProjects();
    return () => {
      cancelled = true;
    };
  }, []);

  const loadBacklog = useCallback(async () => {
    if (!selectedProject) {
      setContent('');
      setBacklogError(null);
      return;
    }

    setBacklogLoading(true);
    setBacklogError(null);
    setContent('');
    try {
      const response = await requestJson<BacklogResponse>(
        `/api/backlog/${encodeURIComponent(selectedProject)}`,
      );
      setContent(response.content);
    } catch (requestError) {
      setBacklogError(errorMessage(requestError));
    } finally {
      setBacklogLoading(false);
    }
  }, [selectedProject]);

  useEffect(() => {
    void loadBacklog();
  }, [loadBacklog]);

  async function handleAppend(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalizedMemo = memo.trim();
    if (!selectedProject || !normalizedMemo) {
      return;
    }

    setAppending(true);
    setBacklogError(null);
    try {
      await requestJson<void>(`/api/backlog/${encodeURIComponent(selectedProject)}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ memo: normalizedMemo }),
      });
      setMemo('');
      await loadBacklog();
    } catch (requestError) {
      setBacklogError(errorMessage(requestError));
    } finally {
      setAppending(false);
    }
  }

  const { mainContent, appendedContent } = splitBacklog(content);

  return (
    <PageFrame
      aside={
        <div className="backlog-project-list">
          <GroupedListSection title="Project">
            {projectsLoading ? (
              <Text c="dimmed" p="md">Projectを読み込んでいます…</Text>
            ) : projects.length === 0 ? (
              <Text c="dimmed" p="md">Projectがありません</Text>
            ) : (
              projects.map((project) => (
                <GroupedListRow
                  key={project}
                  onClick={() => setSelectedProject(project)}
                  rightSection={project === selectedProject ? <Text c="blue" size="sm">選択中</Text> : undefined}
                  selected={project === selectedProject}
                  title={project}
                />
              ))
            )}
          </GroupedListSection>
        </div>
      }
    >
      <Stack gap="md">
        <Title order={1}>Backlog</Title>

        {projectsError && <Alert color="red" title="Projectを取得できませんでした">{projectsError}</Alert>}

        <Paper p="lg" radius="md" shadow="xs" withBorder>
          <Stack gap="md">
            <Title order={2}>{selectedProject ?? 'Projectを選択'}</Title>

            <form onSubmit={handleAppend}>
              <Group align="end" wrap="nowrap">
                <TextInput
                  aria-label="Backlogへ追記するメモ"
                  disabled={!selectedProject || appending}
                  flex={1}
                  onChange={(event) => setMemo(event.currentTarget.value)}
                  placeholder="メモを追記"
                  required
                  value={memo}
                />
                <Button disabled={!selectedProject} loading={appending} type="submit">
                  追記
                </Button>
              </Group>
            </form>

            <Divider />

            {backlogError ? (
              <Alert color="red" title="Backlogを取得できませんでした">{backlogError}</Alert>
            ) : backlogLoading ? (
              <Text c="dimmed">Backlogを読み込んでいます…</Text>
            ) : !selectedProject ? (
              <Text c="dimmed">表示するProjectを選択してください</Text>
            ) : mainContent.trim() === '' && appendedContent.trim() === '' ? (
              <Text c="dimmed" py="xl" ta="center">まだBacklogはありません</Text>
            ) : (
              <Stack gap="md">
                {mainContent.trim() !== '' && (
                  <div className="backlog-markdown">
                    <ReactMarkdown skipHtml>{mainContent}</ReactMarkdown>
                  </div>
                )}
                {appendedContent.trim() !== '' && (
                  <div className="backlog-markdown backlog-appended">
                    <Text c="dimmed" size="sm">未分類メモ</Text>
                    <ReactMarkdown skipHtml>{appendedContent}</ReactMarkdown>
                  </div>
                )}
              </Stack>
            )}
          </Stack>
        </Paper>
      </Stack>
    </PageFrame>
  );
}

function errorMessage(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }
  return '予期しないエラーが発生しました';
}

function splitBacklog(content: string): {
  mainContent: string;
  appendedContent: string;
} {
  const start = content.indexOf(APPENDED_START);
  const end = content.indexOf(APPENDED_END);
  if (start === -1 || end === -1 || start > end) {
    return { mainContent: content, appendedContent: '' };
  }

  return {
    mainContent: content.slice(0, start) + content.slice(end + APPENDED_END.length),
    appendedContent: content.slice(start + APPENDED_START.length, end),
  };
}
