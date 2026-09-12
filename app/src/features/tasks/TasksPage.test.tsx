import { MantineProvider } from "@mantine/core";
import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { TasksPage } from "./TasksPage";

beforeEach(() => {
  vi.stubGlobal(
    "matchMedia",
    vi.fn().mockReturnValue({
      matches: false,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    }),
  );
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: string) => ({
      ok: true,
      json: async () =>
        input === "/api/projects"
          ? { projects: ["whub-dev"] }
          : [
              {
                number: 28,
                title: "Issue一覧",
                url: "https://github.com/Applica-760/whub/issues/28",
              },
            ],
    })),
  );
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("TasksPage", () => {
  it("Project横断のOpen IssueをGitHubへのリンクで表示する", async () => {
    render(
      <MantineProvider env="test">
        <MemoryRouter>
          <TasksPage />
        </MemoryRouter>
      </MantineProvider>,
    );

    const link = await screen.findByRole("link", {
      name: "whub-dev #28 Issue一覧",
    });
    expect(link.getAttribute("href")).toBe(
      "https://github.com/Applica-760/whub/issues/28",
    );
  });
});
