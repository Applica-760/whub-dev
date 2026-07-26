import { describe, expect, it } from "vitest";

import { buildTaskGraphElements } from "./TaskDependencyGraph";

describe("buildTaskGraphElements", () => {
  it("非終端Taskへ至る完了済み依存チェーンを表示する", () => {
    const elements = buildTaskGraphElements([
      {
        id: "TASK-010",
        project: "whub-dev",
        state: "completed",
        title: "依存元",
      },
      {
        depends_on: ["TASK-010"],
        id: "TASK-013",
        project: "whub-dev",
        state: "completed",
        title: "中間Task",
      },
      {
        depends_on: ["TASK-013"],
        id: "TASK-019",
        project: "whub-dev",
        state: "in_progress",
        title: "実行中Task",
      },
    ]);

    expect(elements.map((element) => element.data.id)).toEqual([
      "whub-dev",
      "whub-dev/TASK-010",
      "whub-dev/TASK-013",
      "whub-dev/TASK-019",
      "dependency-whub-dev/TASK-010-whub-dev/TASK-013",
      "dependency-whub-dev/TASK-013-whub-dev/TASK-019",
    ]);
  });

  it("依存チェーンの終端が完了したら全体を表示しない", () => {
    const elements = buildTaskGraphElements([
      { id: "TASK-010", project: "whub-dev", state: "completed" },
      {
        depends_on: ["TASK-010"],
        id: "TASK-013",
        project: "whub-dev",
        state: "completed",
      },
      {
        depends_on: ["TASK-013"],
        id: "TASK-019",
        project: "whub-dev",
        state: "completed",
      },
    ]);

    expect(elements).toEqual([]);
  });

  it("非終端の親へ至る完了済み割り込みチェーンを表示する", () => {
    const elements = buildTaskGraphElements([
      { id: "TASK-010", project: "whub-dev", state: "paused" },
      {
        id: "TASK-013",
        interruption_source_task_id: "TASK-010",
        project: "whub-dev",
        state: "completed",
      },
      {
        id: "TASK-019",
        interruption_source_task_id: "TASK-013",
        project: "whub-dev",
        state: "completed",
      },
    ]);

    expect(elements.map((element) => element.data.id)).toEqual([
      "whub-dev",
      "whub-dev/TASK-010",
      "whub-dev/TASK-013",
      "whub-dev/TASK-019",
      "interrupt-whub-dev/TASK-010-whub-dev/TASK-013",
      "interrupt-whub-dev/TASK-013-whub-dev/TASK-019",
    ]);
  });

  it("非終端Taskの上流ではない完了済み兄弟Taskを表示しない", () => {
    const elements = buildTaskGraphElements([
      { id: "TASK-010", project: "whub-dev", state: "completed" },
      {
        depends_on: ["TASK-010"],
        id: "TASK-013",
        project: "whub-dev",
        state: "completed",
      },
      {
        depends_on: ["TASK-010"],
        id: "TASK-019",
        project: "whub-dev",
        state: "draft",
      },
    ]);

    expect(elements.map((element) => element.data.id)).toEqual([
      "whub-dev",
      "whub-dev/TASK-010",
      "whub-dev/TASK-019",
      "dependency-whub-dev/TASK-010-whub-dev/TASK-019",
    ]);
  });

  it("非終端Taskをブロックするcancelled依存元を表示する", () => {
    const elements = buildTaskGraphElements([
      { id: "TASK-009", project: "whub-dev", state: "cancelled" },
      {
        depends_on: ["TASK-009"],
        id: "TASK-020",
        project: "whub-dev",
        state: "in_progress",
      },
    ]);

    expect(elements.map((element) => element.data.id)).toEqual([
      "whub-dev",
      "whub-dev/TASK-009",
      "whub-dev/TASK-020",
      "dependency-whub-dev/TASK-009-whub-dev/TASK-020",
    ]);
  });

  it("Projectが違う同一Task IDを別ノードとして扱う", () => {
    const elements = buildTaskGraphElements([
      { id: "TASK-001", project: "vault", state: "draft", title: "Vault側" },
      { id: "TASK-001", project: "sns-lab", state: "draft", title: "SNS側" },
    ]);

    expect(elements.map((element) => element.data.id)).toEqual([
      "vault",
      "sns-lab",
      "vault/TASK-001",
      "sns-lab/TASK-001",
    ]);
    expect(elements.map((element) => element.data.label)).toEqual([
      undefined,
      undefined,
      "vault:TASK-001\nVault側",
      "sns-lab:TASK-001\nSNS側",
    ]);
  });

  it("同名IDが他Projectにあっても依存エッジを張らない", () => {
    const elements = buildTaskGraphElements([
      { id: "TASK-001", project: "vault", state: "draft" },
      {
        depends_on: ["TASK-001"],
        id: "TASK-002",
        project: "sns-lab",
        state: "in_progress",
      },
    ]);

    // sns-lab/TASK-002のdepends_onはsns-lab内にしか解決先を探さない
    expect(
      elements.filter((element) => element.data.source != null),
    ).toEqual([]);
  });

  it("ProjectごとのcompoundノードへTaskノードを所属させる", () => {
    const elements = buildTaskGraphElements([
      { id: "TASK-031", project: "whub-dev", state: "in_progress" },
      { id: "TASK-005", project: "la-il", state: "draft" },
      { id: "TASK-007", project: "la-il", state: "draft" },
    ]);

    expect(
      elements
        .filter((element) => element.classes === "project")
        .map((element) => element.data.id),
    ).toEqual(["whub-dev", "la-il"]);
    expect(
      elements
        .filter((element) => element.data.taskId != null)
        .map((element) => element.data.parent),
    ).toEqual(["whub-dev", "la-il", "la-il"]);
  });
});
