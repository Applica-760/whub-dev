import {
  Box,
  Divider,
  Group,
  Paper,
  Stack,
  Text,
  UnstyledButton,
} from "@mantine/core";
import type { ReactNode } from "react";

type GroupedListSectionProps = {
  title?: ReactNode;
  action?: ReactNode;
  children: ReactNode;
};

type GroupedListRowProps = {
  leftSection?: ReactNode;
  title: ReactNode;
  subtitle?: ReactNode;
  rightSection?: ReactNode;
  onClick?: () => void;
  selected?: boolean;
  withDivider?: boolean;
};

export function GroupedListSection({
  title,
  action,
  children,
}: GroupedListSectionProps) {
  return (
    <Stack gap={6}>
      {(title || action) && (
        <Group justify="space-between" px="sm">
          <Text c="dimmed" fw={600} size="sm">
            {title}
          </Text>
          {action}
        </Group>
      )}
      <Paper className="whub-box" radius="md" shadow="xs" withBorder>
        {children}
      </Paper>
    </Stack>
  );
}

export function GroupedListRow({
  leftSection,
  title,
  subtitle,
  rightSection,
  onClick,
  selected = false,
  withDivider = true,
}: GroupedListRowProps) {
  const content = (
    <>
      <Group
        align="center"
        className="grouped-list-row"
        data-selected={selected || undefined}
        gap="sm"
        justify="space-between"
        px="md"
        py="sm"
        wrap="nowrap"
      >
        <Group gap="sm" wrap="nowrap">
          {leftSection}
          <Box>
            <Text fw={500}>{title}</Text>
            {subtitle && (
              <Text c="dimmed" size="sm">
                {subtitle}
              </Text>
            )}
          </Box>
        </Group>
        {rightSection}
      </Group>
      {withDivider && <Divider mx="md" />}
    </>
  );

  if (onClick) {
    return (
      <UnstyledButton aria-pressed={selected} onClick={onClick} w="100%">
        {content}
      </UnstyledButton>
    );
  }

  return content;
}
