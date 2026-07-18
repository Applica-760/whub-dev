import { describe, expect, it } from 'vitest';

import { buildTaskGraphElements } from './TaskDependencyGraph';

describe('buildTaskGraphElements', () => {
  it('完了済みのTASK-010・TASK-013と接続する関係を表示しない', () => {
    const elements = buildTaskGraphElements([
      {
        id: 'TASK-010',
        state: 'completed',
        title: '割り込み元',
      },
      {
        id: 'TASK-013',
        interruption_source_task_id: 'TASK-010',
        state: 'completed',
        title: '割り込みTask',
      },
      {
        depends_on: ['TASK-010'],
        id: 'TASK-019',
        state: 'in_progress',
        title: '実行中Task',
      },
    ]);

    expect(elements.map((element) => element.data.id)).toEqual(['TASK-019']);
  });

  it('cancelled Taskと接続する関係を表示しない', () => {
    const elements = buildTaskGraphElements([
      { id: 'TASK-009', state: 'cancelled' },
      {
        id: 'TASK-017',
        interruption_source_task_id: 'TASK-020',
        state: 'cancelled',
      },
      {
        depends_on: ['TASK-009'],
        id: 'TASK-020',
        state: 'in_progress',
      },
      {
        id: 'TASK-021',
        interruption_source_task_id: 'TASK-009',
        state: 'draft',
      },
    ]);

    expect(elements.map((element) => element.data.id)).toEqual([
      'TASK-020',
      'TASK-021',
    ]);
  });

  it('表示対象Task間の依存・割り込み関係を維持する', () => {
    const elements = buildTaskGraphElements([
      { id: 'TASK-020', state: 'paused' },
      {
        id: 'TASK-021',
        interruption_source_task_id: 'TASK-020',
        state: 'in_progress',
      },
      {
        depends_on: ['TASK-021'],
        id: 'TASK-022',
        state: 'draft',
      },
    ]);

    expect(elements.map((element) => element.data.id)).toEqual([
      'TASK-020',
      'TASK-021',
      'TASK-022',
      'dependency-TASK-021-TASK-022',
      'interrupt-TASK-020-TASK-021',
    ]);
  });
});
