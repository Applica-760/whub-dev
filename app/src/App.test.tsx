import { MantineProvider } from "@mantine/core";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";

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
  it("左右列の折りたたみボタンでTerminalへ状態を渡す", () => {
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
  });
});
