import { describe, expect, it } from 'vitest';

import { isTasksRoute } from './routes';

describe('isTasksRoute', () => {
  it('一覧と詳細をTask領域として判定する', () => {
    expect(isTasksRoute('/tasks')).toBe(true);
    expect(isTasksRoute('/tasks/TASK-012')).toBe(true);
  });

  it('Task以外の画面は判定しない', () => {
    expect(isTasksRoute('/')).toBe(false);
    expect(isTasksRoute('/todos')).toBe(false);
  });
});
