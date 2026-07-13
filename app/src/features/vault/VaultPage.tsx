import { Alert, Box, Group, Text, Tree } from '@mantine/core';
import type { RenderTreeNodePayload, TreeNodeData } from '@mantine/core';
import {
  IconChevronRight,
  IconFileText,
  IconFolder,
  IconFolderOpen,
} from '@tabler/icons-react';
import { useEffect, useState } from 'react';

import type { VaultNode } from '../../api/client';
import { errorMessage } from '../../api/errorMessage';
import { GroupedListSection } from '../../components/GroupedList';
import { MarkdownView } from '../../components/MarkdownView';
import { PageFrame } from '../../components/PageFrame';
import { WidgetFrame } from '../../components/WidgetFrame';
import { fetchVaultNote } from './api';
import { useVaultTree } from './useVaultTree';

function toTreeData(nodes: VaultNode[]): TreeNodeData[] {
  return nodes.map((node) => ({
    value: node.path,
    label: node.name,
    children: node.type === 'directory' ? toTreeData(node.children ?? []) : undefined,
  }));
}

export function VaultPage() {
  const { nodes, loading: treeLoading, error: treeError } = useVaultTree();
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const [content, setContent] = useState('');
  const [noteLoading, setNoteLoading] = useState(false);
  const [noteError, setNoteError] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedPath) {
      return;
    }
    let cancelled = false;
    setNoteLoading(true);
    setNoteError(null);
    fetchVaultNote(selectedPath)
      .then((noteContent) => {
        if (!cancelled) {
          setContent(noteContent);
        }
      })
      .catch((requestError) => {
        if (!cancelled) {
          setNoteError(errorMessage(requestError));
        }
      })
      .finally(() => {
        if (!cancelled) {
          setNoteLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [selectedPath]);

  const renderNode = ({ node, expanded, hasChildren, level, elementProps }: RenderTreeNodePayload) => (
    <Group
      gap={6}
      pr="xs"
      py={4}
      wrap="nowrap"
      {...elementProps}
      className={`${elementProps.className ?? ''} vault-tree-node`}
      data-selected={node.value === selectedPath || undefined}
      onClick={(event) => {
        elementProps.onClick?.(event);
        if (!hasChildren) {
          setSelectedPath(node.value);
        }
      }}
      style={{ paddingInlineStart: 8 + (level - 1) * 8 }}
    >
      {hasChildren ? (
        <>
          <IconChevronRight
            className="vault-tree-icon vault-tree-chevron"
            data-expanded={expanded || undefined}
            size={14}
            stroke={1.5}
          />
          {expanded ? (
            <IconFolderOpen
              className="vault-tree-icon vault-tree-folder-icon"
              size={16}
              stroke={1.5}
            />
          ) : (
            <IconFolder
              className="vault-tree-icon vault-tree-folder-icon"
              size={16}
              stroke={1.5}
            />
          )}
        </>
      ) : (
        <>
          <Box className="vault-tree-icon" w={14} />
          <IconFileText
            className="vault-tree-icon vault-tree-file-icon"
            size={16}
            stroke={1.5}
          />
        </>
      )}
      <Text size="sm" truncate>
        {node.label}
      </Text>
    </Group>
  );

  return (
    <PageFrame
      aside={
        <div className="page-aside-list">
          <GroupedListSection title="Vault">
            {treeLoading ? (
              <Text c="dimmed" p="md">Vaultを読み込んでいます…</Text>
            ) : treeError ? (
              <Alert color="red" m="sm" title="Vaultを取得できませんでした">{treeError}</Alert>
            ) : (
              <Box p="xs">
                <Tree data={toTreeData(nodes)} renderNode={renderNode} />
              </Box>
            )}
          </GroupedListSection>
        </div>
      }
    >
      <WidgetFrame title={<Text c="dimmed" fw={600} size="sm">{selectedPath ?? 'ノートを選択'}</Text>}>
        <Box p="lg">
          {noteError ? (
            <Alert color="red" title="ノートを取得できませんでした">{noteError}</Alert>
          ) : noteLoading ? (
            <Text c="dimmed">ノートを読み込んでいます…</Text>
          ) : !selectedPath ? (
            <Text c="dimmed" py="xl" ta="center">左のツリーからノートを選択してください</Text>
          ) : (
            <MarkdownView content={content} />
          )}
        </Box>
      </WidgetFrame>
    </PageFrame>
  );
}
