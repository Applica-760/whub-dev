import { MantineProvider } from "@mantine/core";
import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";
import { OVERVIEW_COLLAPSE_KEY } from "./features/overview/useOverviewCollapse";

vi.mock("./features/terminal/TerminalPage", () => ({
  TerminalPage: () => <div>Terminal page</div>,
}));

beforeEach(() => {
  localStorage.clear();
  vi.stubGlobal(
    "matchMedia",
    vi.fn().mockReturnValue({
      matches: false,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    }),
  );
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("App Terminal route", () => {
  it("TerminalではOverview用の折りたたみ操作を表示しない", () => {
    localStorage.setItem(OVERVIEW_COLLAPSE_KEY, '{"left":true,"right":false}');

    render(
      <MantineProvider env="test">
        <MemoryRouter initialEntries={["/terminal"]}>
          <App />
        </MemoryRouter>
      </MantineProvider>,
    );

    expect(screen.getByText("Terminal page")).toBeTruthy();
    expect(
      screen.queryByRole("button", { name: "左サイドを折りたたむ" }),
    ).toBeNull();
    expect(localStorage.getItem(OVERVIEW_COLLAPSE_KEY)).toBe(
      '{"left":true,"right":false}',
    );
  });
});
