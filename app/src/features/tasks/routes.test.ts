import { describe, expect, it } from "vitest";

import { isTasksRoute } from "./routes";

describe("isTasksRoute", () => {
  it("一覧をTask領域として判定する", () => {
    expect(isTasksRoute("/tasks")).toBe(true);
    expect(isTasksRoute("/tasks/12")).toBe(false);
  });

  it("Task以外の画面は判定しない", () => {
    expect(isTasksRoute("/")).toBe(false);
    expect(isTasksRoute("/todos")).toBe(false);
  });
});
