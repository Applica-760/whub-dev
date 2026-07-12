import { Alert, Button, Paper, Stack, TextInput, Textarea } from '@mantine/core';
import { useState } from 'react';
import type { FormEvent } from 'react';

import { requestJson } from '../../api/client';
import { errorMessage } from '../../api/errorMessage';
import type { components } from '../../api/generated/schema';
import { PageFrame } from '../../components/PageFrame';

type InboxResponse = components['schemas']['InboxResponse'];

export function InboxPage() {
  const [title, setTitle] = useState('');
  const [body, setBody] = useState('');
  const [filename, setFilename] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!title.trim() || !body.trim()) {
      return;
    }

    setSubmitting(true);
    setError(null);
    setFilename(null);
    try {
      const response = await requestJson<InboxResponse>('/api/inbox', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title, body }),
      });
      setTitle('');
      setBody('');
      setFilename(response.filename);
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <PageFrame>
      <Stack gap="md">
        <Paper p="md" radius="md" shadow="xs" withBorder>
          <form onSubmit={handleSubmit}>
            <Stack gap="sm">
              <TextInput
                aria-label="Inboxノートのタイトル"
                disabled={submitting}
                label="タイトル"
                onChange={(event) => setTitle(event.currentTarget.value)}
                required
                value={title}
                withAsterisk={false}
              />
              <Textarea
                aria-label="Inboxノートの本文"
                autosize
                disabled={submitting}
                label="本文"
                minRows={8}
                onChange={(event) => setBody(event.currentTarget.value)}
                required
                value={body}
                withAsterisk={false}
              />
              <Button loading={submitting} type="submit">保存</Button>
            </Stack>
          </form>
        </Paper>

        {filename && (
          <Alert color="green" title="投函しました">
            <span aria-live="polite">{filename}</span>
          </Alert>
        )}
        {error && <Alert color="red" title="投函できませんでした">{error}</Alert>}
      </Stack>
    </PageFrame>
  );
}
