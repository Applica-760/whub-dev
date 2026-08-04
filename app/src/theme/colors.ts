import type { CSSVariablesResolver } from "@mantine/core";

const palette = {
  background: "#f2f2f7",
  hover: "#ececf0",
  secondaryBackground: "#e5e5ea",
  border: "#c7c7cc",
  subtleText: "#8e8e93",
  mutedText: "#636366",
  text: "#1c1c1e",
  link: "#007aff",
  darkBackground: "rgb(28, 28, 28)",
  darkBoxBackground: "rgb(35, 35, 35)",
} as const;

type ColorScheme = "light" | "dark";
type ColorPair = Record<ColorScheme, string>;

const colorPairs = {
  "--whub-color-page-background": {
    light: palette.background,
    dark: palette.darkBackground,
  },
  "--whub-color-box-background": {
    light: "var(--mantine-color-white)",
    dark: palette.darkBoxBackground,
  },
  "--whub-color-secondary-background": {
    light: palette.secondaryBackground,
    dark: "var(--mantine-color-dark-6)",
  },
  "--whub-color-border": {
    light: palette.border,
    dark: "var(--mantine-color-dark-4)",
  },
  "--whub-color-text": {
    light: palette.text,
    dark: palette.background,
  },
  "--whub-color-text-muted": {
    light: palette.mutedText,
    dark: "var(--mantine-color-dark-1)",
  },
  "--whub-color-text-subtle": {
    light: palette.subtleText,
    dark: "var(--mantine-color-dark-2)",
  },
  "--whub-color-link": {
    light: palette.link,
    dark: "var(--mantine-color-blue-4)",
  },
  "--whub-color-code-block-background": {
    light: palette.text,
    dark: "var(--mantine-color-dark-9)",
  },
  "--whub-color-code-block-text": {
    light: palette.background,
    dark: palette.background,
  },
  "--whub-color-interactive-hover": {
    light: palette.hover,
    dark: "var(--mantine-color-dark-5)",
  },
  "--whub-color-task-graph-node-background": {
    light: "#f8f9fa",
    dark: "#25262b",
  },
  "--whub-color-task-graph-node-border": {
    light: "#868e96",
    dark: "#5c5f66",
  },
  "--whub-color-task-graph-node-text": {
    light: "#212529",
    dark: "#c1c2c5",
  },
  "--whub-color-task-graph-in-progress-background": {
    light: "#e7f5ff",
    dark: "#1864ab",
  },
  "--whub-color-task-graph-in-progress-border": {
    light: "#228be6",
    dark: "#74c0fc",
  },
  "--whub-color-task-graph-paused-background": {
    light: "#fff3bf",
    dark: "#5f3b00",
  },
  "--whub-color-task-graph-paused-border": {
    light: "#f08c00",
    dark: "#ffd43b",
  },
  "--whub-color-task-graph-completed-background": {
    light: "#ebfbee",
    dark: "#1b5e20",
  },
  "--whub-color-task-graph-completed-border": {
    light: "#40c057",
    dark: "#69db7c",
  },
  "--whub-color-task-graph-cancelled-background": {
    light: "#f1f3f5",
    dark: "#373a40",
  },
  "--whub-color-task-graph-cancelled-border": {
    light: "#adb5bd",
    dark: "#5c5f66",
  },
  "--whub-color-task-graph-cancelled-text": {
    light: "#868e96",
    dark: "#909296",
  },
  "--whub-color-task-graph-edge": {
    light: "#adb5bd",
    dark: "#5c5f66",
  },
  "--whub-color-task-graph-interrupt": {
    light: "#eca035",
    dark: "#ffd43b",
  },
  "--whub-color-diff-addition-background": {
    light: "rgba(64, 192, 87, 0.2)",
    dark: "rgba(81, 207, 102, 0.18)",
  },
  "--whub-color-diff-addition-text": {
    light: "#2b8a3e",
    dark: "#8ce99a",
  },
  "--whub-color-diff-deletion-background": {
    light: "rgba(250, 82, 82, 0.18)",
    dark: "rgba(255, 107, 107, 0.18)",
  },
  "--whub-color-diff-deletion-text": {
    light: "#c92a2a",
    dark: "#ffa8a8",
  },
  "--whub-color-diff-hunk-background": {
    light: "rgba(34, 139, 230, 0.18)",
    dark: "rgba(116, 143, 252, 0.18)",
  },
  "--whub-color-diff-hunk-text": {
    light: "#1971c2",
    dark: "#bac8ff",
  },
} satisfies Record<`--whub-color-${string}`, ColorPair>;

function variablesFor(scheme: ColorScheme): Record<string, string> {
  return Object.fromEntries(
    Object.entries(colorPairs).map(([name, pair]) => [name, pair[scheme]]),
  );
}

export const whubCssVariablesResolver: CSSVariablesResolver = () => ({
  variables: {},
  light: variablesFor("light"),
  dark: variablesFor("dark"),
});
