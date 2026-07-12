import { Button, Group, Radio, Select, Stack, TextInput } from '@mantine/core';
import { useState } from 'react';
import type { FormEvent } from 'react';

import type { TodoCreateInput } from './api';

type TodoFormProps = {
  projects: string[];
  submitting: boolean;
  onCreate: (input: TodoCreateInput) => Promise<boolean>;
};

const priorityOptions = [
  { value: 'none', color: 'gray' },
  { value: 'red', color: 'red' },
  { value: 'yellow', color: 'yellow' },
  { value: 'blue', color: 'blue' },
] as const;

export function TodoForm({ projects, submitting, onCreate }: TodoFormProps) {
  const [title, setTitle] = useState('');
  const [project, setProject] = useState<string | null>(null);
  const [priority, setPriority] = useState<TodoCreateInput['priority']>('none');
  const [dueDate, setDueDate] = useState('');

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalizedTitle = title.trim();
    if (!normalizedTitle) {
      return;
    }

    const created = await onCreate({
      title: normalizedTitle,
      project,
      priority,
      due_date: dueDate || null,
    });
    if (created) {
      setTitle('');
      setProject(null);
      setPriority('none');
      setDueDate('');
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <Stack gap="sm">
        <Group align="end" wrap="nowrap">
          <TextInput
            aria-label="Todoのタイトル"
            disabled={submitting}
            flex={1}
            onChange={(event) => setTitle(event.currentTarget.value)}
            placeholder="次にすること"
            required
            value={title}
          />
          <Button loading={submitting} type="submit">追加</Button>
        </Group>
        <Group align="end" grow>
          <Select
            clearable
            data={projects}
            disabled={submitting}
            label="Project"
            onChange={setProject}
            placeholder="指定なし"
            value={project}
          />
          <Radio.Group
            label="優先度"
            onChange={(value) => setPriority(value as TodoCreateInput['priority'])}
            value={priority}
          >
            <Group gap="sm" mt="xs">
              {priorityOptions.map((option) => (
                <Radio
                  aria-label={option.value}
                  color={option.color}
                  disabled={submitting}
                  key={option.value}
                  value={option.value}
                />
              ))}
            </Group>
          </Radio.Group>
          <TextInput
            disabled={submitting}
            label="期限"
            onChange={(event) => setDueDate(event.currentTarget.value)}
            type="date"
            value={dueDate}
          />
        </Group>
      </Stack>
    </form>
  );
}
