import { MantineProvider } from '@mantine/core';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { TaskDetailPage } from './TaskDetailPage';

vi.mock('./TaskFlowGraphWidget', () => ({
  TaskFlowGraphWidget: () => null,
}));

beforeEach(() => {
  vi.stubGlobal('matchMedia', vi.fn().mockReturnValue({
    matches: false,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
  }));
});

afterEach(() => {
  vi.unstubAllGlobals();
});

function response(body: unknown): Response {
  return {
    ok: true,
    json: async () => body,
  } as Response;
}

describe('TaskDetailPage', () => {
  it('stateの上にTask IDを表示する', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response({
      schema_version: 1,
      task: {
        id: 'TASK-012',
        state: 'in_progress',
        title: '開発モード',
        objective: '確認を速くする',
        approach: [],
        depends_on: [],
        interruption_task_id: null,
        interruption_reason: null,
        interruption_source_task_id: null,
      },
      plan: null,
      approvals: [],
      acceptance_results: [],
      change_requests: [],
      cancellation: null,
      result: null,
    })));

    render(
      <MantineProvider env="test">
        <MemoryRouter initialEntries={['/tasks/TASK-012']}>
          <Routes>
            <Route path="/tasks/:taskId" element={<TaskDetailPage />} />
          </Routes>
        </MemoryRouter>
      </MantineProvider>,
    );

    expect(await screen.findByText('Task ID: TASK-012')).toBeTruthy();
    expect(screen.getByText('state: in_progress')).toBeTruthy();
  });
});
