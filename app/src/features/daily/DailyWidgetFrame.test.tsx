import { MantineProvider } from "@mantine/core";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { DailyWidgetFrame } from "./DailyWidgetFrame";

function response(body: unknown): Response {
  return {
    ok: true,
    json: async () => body,
  } as Response;
}

function renderWidget() {
  return render(
    <MantineProvider env="test">
      <DailyWidgetFrame />
    </MantineProvider>,
  );
}

beforeEach(() => {
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

describe("DailyWidgetFrame", () => {
  it("InboxとDailyの下書きを切替後も保持する", () => {
    renderWidget();

    fireEvent.change(screen.getByLabelText("Inboxノートのタイトル"), {
      target: { value: "inbox title" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Daily" }));
    fireEvent.change(screen.getByLabelText("Dailyログの本文"), {
      target: { value: "daily body" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Inbox" }));

    expect(
      (screen.getByLabelText("Inboxノートのタイトル") as HTMLInputElement).value,
    ).toBe("inbox title");
    fireEvent.click(screen.getByRole("button", { name: "Daily" }));
    expect(
      (screen.getByLabelText("Dailyログの本文") as HTMLTextAreaElement).value,
    ).toBe("daily body");
    expect(screen.getByRole("button", { name: "Daily" }).getAttribute("aria-pressed")).toBe(
      "true",
    );
  });

  it("Daily投稿で本文と元気度をAPIへ送る", async () => {
    const fetchMock = vi.fn().mockResolvedValue(response({ path: "daily/2026-07-28.md" }));
    vi.stubGlobal("fetch", fetchMock);
    renderWidget();

    fireEvent.click(screen.getByRole("button", { name: "Daily" }));
    fireEvent.change(screen.getByLabelText("Dailyログの本文"), {
      target: { value: "今日は元気" },
    });
    const energyInput = screen.getByLabelText("元気度 4");
    const energyLabel = document.querySelector(
      `label[for="${energyInput.id}"]`,
    );
    if (energyLabel === null) {
      throw new Error("energy label is missing");
    }
    fireEvent.click(energyLabel);
    fireEvent.click(screen.getByRole("button", { name: "記録" }));

    expect(await screen.findByText("daily/2026-07-28.md")).toBeTruthy();
    expect(fetchMock).toHaveBeenCalledWith("/api/daily", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ body: "今日は元気", energy: 4 }),
    });
  });
});
