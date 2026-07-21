import {
  Alert,
  Box,
  Button,
  Divider,
  Group,
  Stack,
  Text,
  TextInput,
} from "@mantine/core";
import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";

import { type BacklogResponse, requestJson } from "../../api/client";
import { errorMessage } from "../../api/errorMessage";
import { MarkdownView } from "../../components/MarkdownView";
import { WidgetFrame } from "../../components/WidgetFrame";

const APPENDED_START = "<!-- hub:backlog:appended:start -->";
const APPENDED_END = "<!-- hub:backlog:appended:end -->";

type BacklogWidgetProps = {
  project: string | null;
};

export function BacklogWidget({ project }: BacklogWidgetProps) {
  const [content, setContent] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [memo, setMemo] = useState("");
  const [appending, setAppending] = useState(false);

  const loadBacklog = useCallback(async () => {
    if (!project) {
      setContent("");
      setError(null);
      return;
    }

    setLoading(true);
    setError(null);
    setContent("");
    try {
      const response = await requestJson<BacklogResponse>(
        `/api/backlog/${encodeURIComponent(project)}`,
      );
      setContent(response.content);
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setLoading(false);
    }
  }, [project]);

  useEffect(() => {
    void loadBacklog();
  }, [loadBacklog]);

  async function handleAppend(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalizedMemo = memo.trim();
    if (!project || !normalizedMemo) {
      return;
    }

    setAppending(true);
    setError(null);
    try {
      await requestJson<void>(`/api/backlog/${encodeURIComponent(project)}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ memo: normalizedMemo }),
      });
      setMemo("");
      await loadBacklog();
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setAppending(false);
    }
  }

  const { mainContent, appendedContent } = splitBacklog(content);

  return (
    <WidgetFrame
      title={
        <Text c="dimmed" fw={600} size="sm">
          {project ?? "Projectを選択"}
        </Text>
      }
    >
      <Box p="lg">
        <Stack gap="md">
          <form onSubmit={handleAppend}>
            <Group align="end" wrap="nowrap">
              <TextInput
                aria-label="Backlogへ追記するメモ"
                disabled={!project || appending}
                flex={1}
                onChange={(event) => setMemo(event.currentTarget.value)}
                placeholder="メモを追記"
                required
                value={memo}
              />
              <Button disabled={!project} loading={appending} type="submit">
                追記
              </Button>
            </Group>
          </form>

          <Divider />

          {error ? (
            <Alert color="red" title="Backlogを取得できませんでした">
              {error}
            </Alert>
          ) : loading ? (
            <Text c="dimmed">Backlogを読み込んでいます…</Text>
          ) : !project ? (
            <Text c="dimmed">表示するProjectを選択してください</Text>
          ) : mainContent.trim() === "" && appendedContent.trim() === "" ? (
            <Text c="dimmed" py="xl" ta="center">
              まだBacklogはありません
            </Text>
          ) : (
            <Stack gap="md">
              {mainContent.trim() !== "" && (
                <MarkdownView content={mainContent} />
              )}
              {appendedContent.trim() !== "" && (
                <div className="backlog-appended">
                  <Text c="dimmed" size="sm">
                    未分類メモ
                  </Text>
                  <MarkdownView content={appendedContent} />
                </div>
              )}
            </Stack>
          )}
        </Stack>
      </Box>
    </WidgetFrame>
  );
}

function splitBacklog(content: string): {
  mainContent: string;
  appendedContent: string;
} {
  const start = content.indexOf(APPENDED_START);
  const end = content.indexOf(APPENDED_END);
  if (start === -1 || end === -1 || start > end) {
    return { mainContent: content, appendedContent: "" };
  }

  return {
    mainContent:
      content.slice(0, start) + content.slice(end + APPENDED_END.length),
    appendedContent: content.slice(start + APPENDED_START.length, end),
  };
}
