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
