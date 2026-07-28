import { Alert, Box, Button, Group, Rating, Stack, Text, Textarea } from "@mantine/core";
import { useState } from "react";
import type { FormEvent } from "react";

import { requestJson } from "../../api/client";
import { errorMessage } from "../../api/errorMessage";
import type { components } from "../../api/generated/schema";

type DailyEntryResponse = components["schemas"]["DailyEntryResponse"];

export function DailyForm() {
  const [body, setBody] = useState("");
  const [energy, setEnergy] = useState<number | null>(null);
  const [path, setPath] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function handleEnergyChange(value: number) {
    setEnergy((current) => (current === value ? null : value));
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!body.trim()) {
      return;
    }

    setSubmitting(true);
    setError(null);
    setPath(null);
    try {
      const response = await requestJson<DailyEntryResponse>("/api/daily", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ body, energy }),
      });
      setBody("");
      setEnergy(null);
      setPath(response.path);
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Box p="md">
      <form onSubmit={handleSubmit}>
        <Stack gap="sm">
          <Textarea
            aria-label="Dailyログの本文"
            autosize
            disabled={submitting}
            label="How are you feeling?"
            minRows={8}
            onChange={(event) => setBody(event.currentTarget.value)}
            required
            value={body}
            withAsterisk={false}
          />
          <Group gap="sm">
            <Text size="sm">Satisfaction</Text>
            <Rating
              color="blue"
              count={5}
              getSymbolLabel={(value) => `Satisfaction ${value}`}
              onChange={handleEnergyChange}
              readOnly={submitting}
              value={energy ?? 0}
            />
          </Group>
          <Button loading={submitting} type="submit">
            記録
          </Button>
          {path && (
            <Alert color="green" title="記録しました">
              <span aria-live="polite">{path}</span>
            </Alert>
          )}
          {error && (
            <Alert color="red" title="記録できませんでした">
              {error}
            </Alert>
          )}
        </Stack>
      </form>
    </Box>
  );
}
