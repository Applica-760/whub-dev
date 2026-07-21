import { Paper, Stack, Text, Title } from "@mantine/core";

type PlaceholderPageProps = {
  title: string;
  description: string;
};

export function PlaceholderPage({ title, description }: PlaceholderPageProps) {
  return (
    <Paper className="whub-box" p="lg" radius="md" withBorder>
      <Stack gap="xs">
        <Title order={1}>{title}</Title>
        <Text c="dimmed">{description}</Text>
      </Stack>
    </Paper>
  );
}
