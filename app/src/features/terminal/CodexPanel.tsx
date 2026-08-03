import { Alert, Button, Group, Stack, Text, Textarea } from "@mantine/core";
import { useCallback, useEffect, useState } from "react";

import { requestJson } from "../../api/client";

type AgentMessage = { turn_id: string; text: string };
type Approval = {
  request_id: string | number;
  command: string | null;
  cwd: string | null;
  reason: string | null;
};
type State = {
  active_turn_id: string | null;
  messages: AgentMessage[];
  approvals: Approval[];
  error: string | null;
};

export function CodexPanel({
  project,
  taskId,
}: {
  project: string;
  taskId: string;
}) {
  const [prompt, setPrompt] = useState("");
  const [state, setState] = useState<State | null>(null);
  const [error, setError] = useState<string | null>(null);
  const base = `/api/agent-codex/${encodeURIComponent(project)}/${encodeURIComponent(taskId)}`;

  const refresh = useCallback(async () => {
    try {
      setState(await requestJson<State>(base));
      setError(null);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Codexを読み込めませんでした。",
      );
    }
  }, [base]);

  useEffect(() => {
    void refresh();
    const interval = window.setInterval(() => void refresh(), 1000);
    return () => window.clearInterval(interval);
  }, [refresh]);

  const send = useCallback(async () => {
    if (!prompt.trim()) return;
    try {
      await requestJson<void>(`${base}/turns`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt }),
      });
      setPrompt("");
      void refresh();
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "送信できませんでした。",
      );
    }
  }, [base, prompt, refresh]);

  const decide = useCallback(
    async (requestId: string | number, decision: "accept" | "decline") => {
      try {
        await requestJson<void>(
          `${base}/approvals/${encodeURIComponent(String(requestId))}`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ decision }),
          },
        );
        void refresh();
      } catch (requestError) {
        setError(
          requestError instanceof Error
            ? requestError.message
            : "承認を送信できませんでした。",
        );
      }
    },
    [base, refresh],
  );

  return (
    <Stack gap="sm" p="md">
      <Text fw={600}>Codex</Text>
      {error && <Alert color="red">{error}</Alert>}
      {state?.error && <Alert color="red">{state.error}</Alert>}
      {(state?.approvals ?? []).map((approval) => (
        <Alert
          color="yellow"
          key={String(approval.request_id)}
          title="コマンドの承認が必要です"
        >
          <Text ff="monospace" size="sm">
            {approval.command ?? approval.reason ?? "Codex command"}
          </Text>
          {approval.cwd && (
            <Text c="dimmed" size="xs">
              {approval.cwd}
            </Text>
          )}
          <Group mt="xs">
            <Button
              color="green"
              disabled={Boolean(state?.error)}
              onClick={() => void decide(approval.request_id, "accept")}
              size="xs"
            >
              許可
            </Button>
            <Button
              color="red"
              disabled={Boolean(state?.error)}
              onClick={() => void decide(approval.request_id, "decline")}
              size="xs"
              variant="light"
            >
              拒否
            </Button>
          </Group>
        </Alert>
      ))}
      <Stack gap={2} mah={240} style={{ overflowY: "auto" }}>
        {(state?.messages ?? []).map((message, index) => (
          <Text
            key={`${message.turn_id}-${index}`}
            size="sm"
            style={{ whiteSpace: "pre-wrap" }}
          >
            {message.text}
          </Text>
        ))}
      </Stack>
      <Textarea
        autosize
        minRows={2}
        onChange={(event) => setPrompt(event.currentTarget.value)}
        placeholder="Codexへ依頼…"
        value={prompt}
      />
      <Button
        disabled={
          !prompt.trim() ||
          state?.active_turn_id !== null ||
          Boolean(state?.error)
        }
        onClick={() => void send()}
      >
        送信
      </Button>
    </Stack>
  );
}
