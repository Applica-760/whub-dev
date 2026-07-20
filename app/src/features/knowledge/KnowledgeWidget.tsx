import {
  Alert,
  Badge,
  Box,
  Code,
  Group,
  Paper,
  Stack,
  Tabs,
  Text,
  TextInput,
} from '@mantine/core';
import { useCallback, useEffect, useState } from 'react';

import {
  ApiError,
  type KnowledgeResponse,
  requestJson,
} from '../../api/client';
import { errorMessage } from '../../api/errorMessage';
import { WidgetFrame } from '../../components/WidgetFrame';

type MappingCategory = 'definitions' | 'policies' | 'constraints' | 'exceptions';
type Category = MappingCategory | 'relations';
type SelectedCategory = 'all' | Category;
type MappingEntry = KnowledgeResponse[MappingCategory][string];
type KnowledgeEntry = MappingEntry | KnowledgeResponse['relations'][number];
type KnowledgeItem = {
  key: string;
  entry: KnowledgeEntry;
};

const CATEGORY_LABELS: Record<Category, string> = {
  definitions: 'DEF',
  relations: 'REL',
  policies: 'POL',
  constraints: 'CON',
  exceptions: 'EXC',
};

const CATEGORY_PREFIXES: Record<MappingCategory, string> = {
  definitions: 'def',
  policies: 'pol',
  constraints: 'con',
  exceptions: 'exc',
};

type KnowledgeWidgetProps = {
  project: string | null;
};

export function KnowledgeWidget({ project }: KnowledgeWidgetProps) {
  const [knowledge, setKnowledge] = useState<KnowledgeResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [missing, setMissing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [category, setCategory] = useState<SelectedCategory>('all');
  const [query, setQuery] = useState('');

  const loadKnowledge = useCallback(async () => {
    if (!project) {
      setKnowledge(null);
      setMissing(false);
      setError(null);
      return;
    }

    setLoading(true);
    setMissing(false);
    setError(null);
    setKnowledge(null);
    try {
      setKnowledge(await requestJson<KnowledgeResponse>(
        `/api/knowledge/${encodeURIComponent(project)}`,
      ));
    } catch (requestError) {
      if (requestError instanceof ApiError && requestError.status === 404) {
        setMissing(true);
      } else {
        setError(errorMessage(requestError));
      }
    } finally {
      setLoading(false);
    }
  }, [project]);

  useEffect(() => {
    void loadKnowledge();
  }, [loadKnowledge]);

  const groups = knowledgeGroups(knowledge, category, query);
  const entryCount = groups.reduce((count, group) => count + group.entries.length, 0);

  return (
    <WidgetFrame title={<Text c="dimmed" fw={600} size="sm">{project ?? 'Projectを選択'}</Text>}>
      <Box p="lg">
        <Stack gap="md">
          <TextInput
            aria-label="Knowledgeを検索"
            disabled={!knowledge}
            onChange={(event) => setQuery(event.currentTarget.value)}
            placeholder="ID・用語・本文を検索"
            value={query}
          />

          <Tabs
            onChange={(value) => setCategory((value as SelectedCategory | null) ?? 'all')}
            value={category}
          >
            <Tabs.List>
              <Tabs.Tab value="all">All</Tabs.Tab>
              {Object.entries(CATEGORY_LABELS).map(([value, label]) => (
                <Tabs.Tab key={value} value={value}>{label}</Tabs.Tab>
              ))}
            </Tabs.List>
          </Tabs>

          {error ? (
            <Alert color="red" title="Knowledgeを取得できませんでした">{error}</Alert>
          ) : loading ? (
            <Text c="dimmed">Knowledgeを読み込んでいます…</Text>
          ) : !project ? (
            <Text c="dimmed">表示するProjectを選択してください</Text>
          ) : missing ? (
            <Text c="dimmed" py="xl" ta="center">Knowledgeはありません</Text>
          ) : knowledge && entryCount === 0 ? (
            <Text c="dimmed" py="xl" ta="center">該当するKnowledgeはありません</Text>
          ) : (
            groups.map((group) => (
              <Stack gap="xs" key={group.category}>
                <Text c="dimmed" fw={600} size="sm">
                  {CATEGORY_LABELS[group.category]} ({group.entries.length})
                </Text>
                {group.entries.map((item) => (
                  <KnowledgeEntryCard item={item} key={item.key} />
                ))}
              </Stack>
            ))
          )}
        </Stack>
      </Box>
    </WidgetFrame>
  );
}

function knowledgeGroups(
  knowledge: KnowledgeResponse | null,
  selected: SelectedCategory,
  query: string,
): Array<{ category: Category; entries: KnowledgeItem[] }> {
  if (!knowledge) {
    return [];
  }

  const normalizedQuery = query.trim().toLocaleLowerCase();
  const categories = Object.keys(CATEGORY_LABELS) as Category[];
  return categories
    .filter((category) => selected === 'all' || category === selected)
    .map((category) => {
      const entries: KnowledgeItem[] = category === 'relations'
        ? knowledge.relations.map((entry) => ({
            key: `${entry.subject} ${entry.predicate} ${entry.object}`,
            entry,
          }))
        : Object.entries(
            knowledge[category] as Record<string, MappingEntry>,
          ).map(([slug, entry]) => ({
            key: `${CATEGORY_PREFIXES[category]}:${slug}`,
            entry,
          }));
      return {
        category,
        entries: entries.filter(({ key, entry }) => (
          !normalizedQuery || [key, ...Object.values(entry)].some((value) => (
          typeof value === 'string' && value.toLocaleLowerCase().includes(normalizedQuery)
          ))
        )),
      };
    })
    .filter((group) => group.entries.length > 0);
}

function KnowledgeEntryCard({ item }: { item: KnowledgeItem }) {
  const { key, entry } = item;
  return (
    <Paper className="whub-box" p="md" radius="md" withBorder>
      <Stack gap="sm">
        <Group justify="space-between" wrap="nowrap">
          <Badge variant="light">{key}</Badge>
          {entry.ref && <Code>{entry.ref}</Code>}
        </Group>
        <KnowledgeEntryContent entry={entry} />
      </Stack>
    </Paper>
  );
}

function KnowledgeEntryContent({ entry }: { entry: KnowledgeEntry }) {
  if ('definition' in entry) {
    return (
      <Text>
        <Text component="span" fw={600}>{entry.name}</Text>
        ：{entry.definition}
      </Text>
    );
  }
  if ('predicate' in entry) {
    return (
      <Group gap="xs">
        <Code>{entry.subject}</Code>
        <Text>{entry.predicate}</Text>
        <Code>{entry.object}</Code>
        {entry.cardinality && <Text c="dimmed">({entry.cardinality})</Text>}
      </Group>
    );
  }
  if ('condition' in entry) {
    return (
      <Stack gap={4}>
        <Text>{entry.statement}</Text>
        <Text c="dimmed" size="sm">条件: {entry.condition}</Text>
      </Stack>
    );
  }
  return <Text>{entry.statement}</Text>;
}
