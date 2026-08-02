import { MantineProvider } from "@mantine/core";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";
import { OVERVIEW_COLLAPSE_KEY } from "./features/overview/useOverviewCollapse";
import { TERMINAL_COLLAPSE_KEY } from "./features/terminal/useTerminalCollapse";

vi.mock("./features/terminal/TerminalPage", () => ({
  TerminalPage: ({
    collapsed,
  }: {
    collapsed: { left: boolean; right: boolean };
  }) => <div>{JSON.stringify(collapsed)}</div>,
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
  it("Terminal固有の折りたたみ状態だけを操作する", () => {
    localStorage.setItem(OVERVIEW_COLLAPSE_KEY, '{"left":true,"right":false}');
    localStorage.setItem(TERMINAL_COLLAPSE_KEY, '{"left":false,"right":false}');

    render(
      <MantineProvider env="test">
        <MemoryRouter initialEntries={["/terminal"]}>
          <App />
        </MemoryRouter>
      </MantineProvider>,
    );

    expect(screen.getByText('{"left":false,"right":false}')).toBeTruthy();
    fireEvent.click(
      screen.getByRole("button", { name: "左サイドを折りたたむ" }),
    );

    expect(screen.getByText('{"left":true,"right":false}')).toBeTruthy();
    expect(
      screen.getByRole("button", { name: "左サイドを展開する" }),
    ).toBeTruthy();
    expect(localStorage.getItem(OVERVIEW_COLLAPSE_KEY)).toBe(
      '{"left":true,"right":false}',
    );
    expect(localStorage.getItem(TERMINAL_COLLAPSE_KEY)).toBe(
      '{"left":true,"right":false}',
    );
  });
});
