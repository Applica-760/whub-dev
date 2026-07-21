import {
  ActionIcon,
  useComputedColorScheme,
  useMantineColorScheme,
} from "@mantine/core";
import { IconMoon, IconSun } from "@tabler/icons-react";

export function ColorSchemeToggle() {
  const colorScheme = useComputedColorScheme("light");
  const { setColorScheme } = useMantineColorScheme();
  const nextColorScheme = colorScheme === "dark" ? "light" : "dark";
  const label = `${nextColorScheme === "dark" ? "ダーク" : "ライト"}テーマに切り替える`;

  return (
    <ActionIcon
      aria-label={label}
      className="whub-color-scheme-toggle"
      onClick={() => setColorScheme(nextColorScheme)}
      title={label}
      variant="subtle"
    >
      {nextColorScheme === "dark" ? (
        <IconMoon aria-hidden size={18} stroke={1.5} />
      ) : (
        <IconSun aria-hidden size={18} stroke={1.5} />
      )}
    </ActionIcon>
  );
}
