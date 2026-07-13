import { MantineProvider } from '@mantine/core';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import type { KnowledgeResponse } from '../../api/client';
import { KnowledgePage } from './KnowledgePage';
import { KnowledgeWidget } from './KnowledgeWidget';

const KNOWLEDGE = {
  schema_version: 3,
  definitions: [
    { id: 'DEF-001', name: 'whub', definition: 'projectを統合管理するCLI' },
  ],
  relation_types: [
    { name: 'manages', definition: 'subjectがobjectを管理する' },
  ],
  relations: [
    { id: 'REL-001', subject: 'DEF-001', predicate: 'manages', object: 'DEF-001' },
  ],
  policies: [
    { id: 'POL-001', statement: 'Knowledge YAMLをSSOTとする' },
  ],
  constraints: [
    { id: 'CON-001', statement: '未知フィールドを拒否する' },
  ],
  exceptions: [],
} satisfies KnowledgeResponse;

beforeEach(() => {
  vi.stubGlobal('matchMedia', vi.fn().mockReturnValue({
    matches: false,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
  }));
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

function response(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: status === 404 ? 'Not Found' : 'Server Error',
    json: async () => body,
  } as Response;
}

function renderInMantine(component: React.ReactNode) {
  return render(<MantineProvider env="test">{component}</MantineProvider>);
}

describe('KnowledgeWidget', () => {
  it('分類タブと検索で表示を絞り込む', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response(KNOWLEDGE)));
    renderInMantine(<KnowledgeWidget project="workspace-hub" />);

    await screen.findAllByText('DEF-001');
    fireEvent.click(screen.getByRole('tab', { name: 'CON' }));
    expect(screen.getByText('CON-001')).toBeTruthy();
    expect(screen.queryByText('DEF-001')).toBeNull();

    fireEvent.click(screen.getByRole('tab', { name: 'All' }));
    fireEvent.change(screen.getByLabelText('Knowledgeを検索'), {
      target: { value: 'POL-001' },
    });
    expect(screen.getByText('POL-001')).toBeTruthy();
    expect(screen.queryByText('CON-001')).toBeNull();

    fireEvent.change(screen.getByLabelText('Knowledgeを検索'), {
      target: { value: 'not-found' },
    });
    expect(screen.getByText('該当するKnowledgeはありません')).toBeTruthy();
  });

  it.each([
    [404, 'Knowledgeはありません'],
    [500, 'Knowledgeを取得できませんでした'],
  ])('取得失敗status %sを区別して表示する', async (status, expected) => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(response({ detail: 'request failed' }, status)),
    );
    renderInMantine(<KnowledgeWidget project="workspace-hub" />);

    expect(await screen.findByText(expected)).toBeTruthy();
  });
});

describe('KnowledgePage', () => {
  it('workspace-hubを初期選択し、project切替で再取得する', async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const path = String(input);
      if (path === '/api/projects') {
        return Promise.resolve(response({ projects: ['local', 'workspace-hub'] }));
      }
      return Promise.resolve(response(KNOWLEDGE));
    });
    vi.stubGlobal('fetch', fetchMock);
    renderInMantine(<KnowledgePage />);

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith('/api/knowledge/workspace-hub', undefined);
    });
    fireEvent.click(screen.getByText('local'));
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith('/api/knowledge/local', undefined);
    });
  });
});
