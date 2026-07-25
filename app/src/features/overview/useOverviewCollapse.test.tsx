import { MantineProvider } from "@mantine/core";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { OverviewCollapseToggles } from "./OverviewCollapseToggles";
import { OverviewFrame, OverviewSide } from "./OverviewFrame";
import {
  OVERVIEW_COLLAPSE_KEY,
  useOverviewCollapse,
} from "./useOverviewCollapse";

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

// headerのトグルとOverview本体が同じstateを共有する実配置を再現する
function Harness() {
  const { collapsed, toggle } = useOverviewCollapse();

  return (
    <>
      <OverviewCollapseToggles collapsed={collapsed} onToggle={toggle} />
      <OverviewFrame collapsed={collapsed}>
        <OverviewSide collapsed={collapsed.left} side="left">
          <div>左の中身</div>
        </OverviewSide>
        <OverviewSide collapsed={collapsed.right} side="right">
          <div>右の中身</div>
        </OverviewSide>
      </OverviewFrame>
    </>
  );
}

function renderHarness() {
  return render(
    <MantineProvider env="test">
      <Harness />
    </MantineProvider>,
  );
}

function frame() {
  const element = document.querySelector(".overview-frame");
  if (!element) {
    throw new Error("overview-frameが描画されていない");
  }
  return element;
}

function side(name: string) {
  const element = document.querySelector(`[data-side="${name}"]`);
  if (!element) {
    throw new Error(`${name}サイドが描画されていない`);
  }
  return element;
}

describe("useOverviewCollapse", () => {
  it("片側だけ折りたたみ、状態をlocalStorageへ永続化する", () => {
    renderHarness();

    expect(frame().getAttribute("data-collapse-left")).toBe("false");
    fireEvent.click(
      screen.getByRole("button", { name: "左サイドを折りたたむ" }),
    );

    expect(frame().getAttribute("data-collapse-left")).toBe("true");
    expect(frame().getAttribute("data-collapse-right")).toBe("false");
    expect(side("left").getAttribute("data-collapsed")).toBe("true");
    expect(side("right").getAttribute("data-collapsed")).toBe("false");
    expect(localStorage.getItem(OVERVIEW_COLLAPSE_KEY)).toBe(
      '{"left":true,"right":false}',
    );
    // 折りたたみ中もwidgetはmountされたままにする
    expect(screen.getByText("左の中身")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "左サイドを展開する" }));
    expect(frame().getAttribute("data-collapse-left")).toBe("false");
  });

  it("初回描画から保存済みの折りたたみ状態を復元する", () => {
    localStorage.setItem(OVERVIEW_COLLAPSE_KEY, '{"left":false,"right":true}');
    renderHarness();

    expect(frame().getAttribute("data-collapse-right")).toBe("true");
    expect(
      screen.getByRole("button", { name: "右サイドを展開する" }),
    ).toBeTruthy();
  });

  it("壊れた保存値では両側を展開状態にする", () => {
    localStorage.setItem(OVERVIEW_COLLAPSE_KEY, "not-json");
    renderHarness();

    expect(frame().getAttribute("data-collapse-left")).toBe("false");
    expect(frame().getAttribute("data-collapse-right")).toBe("false");
  });
});
