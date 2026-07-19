import { describe, expect, it } from 'vitest';

import { buildTaskGraphElements } from './TaskDependencyGraph';

describe('buildTaskGraphElements', () => {
  it('非終端Taskへ至る完了済み依存チェーンを表示する', () => {
    const elements = buildTaskGraphElements([
      {
        id: 'TASK-010',
        state: 'completed',
        title: '依存元',
      },
      {
        depends_on: ['TASK-010'],
        id: 'TASK-013',
        state: 'completed',
        title: '中間Task',
      },
      {
        depends_on: ['TASK-013'],
        id: 'TASK-019',
        state: 'in_progress',
        title: '実行中Task',
      },
    ]);

    expect(elements.map((element) => element.data.id)).toEqual([
      'TASK-010',
      'TASK-013',
      'TASK-019',
      'dependency-TASK-010-TASK-013',
      'dependency-TASK-013-TASK-019',
    ]);
  });

  it('依存チェーンの終端が完了したら全体を表示しない', () => {
    const elements = buildTaskGraphElements([
      { id: 'TASK-010', state: 'completed' },
      {
        depends_on: ['TASK-010'],
        id: 'TASK-013',
        state: 'completed',
      },
      {
        depends_on: ['TASK-013'],
        id: 'TASK-019',
        state: 'completed',
      },
    ]);

    expect(elements).toEqual([]);
  });

  it('非終端の親へ至る完了済み割り込みチェーンを表示する', () => {
    const elements = buildTaskGraphElements([
      { id: 'TASK-010', state: 'paused' },
      {
        id: 'TASK-013',
        interruption_source_task_id: 'TASK-010',
        state: 'completed',
      },
      {
        id: 'TASK-019',
        interruption_source_task_id: 'TASK-013',
        state: 'completed',
      },
    ]);

    expect(elements.map((element) => element.data.id)).toEqual([
      'TASK-010',
      'TASK-013',
      'TASK-019',
      'interrupt-TASK-010-TASK-013',
      'interrupt-TASK-013-TASK-019',
    ]);
  });

  it('非終端Taskの上流ではない完了済み兄弟Taskを表示しない', () => {
    const elements = buildTaskGraphElements([
      { id: 'TASK-010', state: 'completed' },
      {
        depends_on: ['TASK-010'],
        id: 'TASK-013',
        state: 'completed',
      },
      {
        depends_on: ['TASK-010'],
        id: 'TASK-019',
        state: 'draft',
      },
    ]);

    expect(elements.map((element) => element.data.id)).toEqual([
      'TASK-010',
      'TASK-019',
      'dependency-TASK-010-TASK-019',
    ]);
  });

  it('非終端Taskをブロックするcancelled依存元を表示する', () => {
    const elements = buildTaskGraphElements([
      { id: 'TASK-009', state: 'cancelled' },
      {
        depends_on: ['TASK-009'],
        id: 'TASK-020',
        state: 'in_progress',
      },
    ]);

    expect(elements.map((element) => element.data.id)).toEqual([
      'TASK-009',
      'TASK-020',
      'dependency-TASK-009-TASK-020',
    ]);
  });
});
