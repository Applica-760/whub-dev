import { Alert, Box, Group, Loader, ScrollArea, Text } from "@mantine/core";
import {
  IconChevronRight,
  IconFile,
  IconFolder,
  IconFolderOpen,
} from "@tabler/icons-react";
import { useEffect, useState } from "react";
import type { ReactNode } from "react";

import { requestJson } from "../../../api/client";
import { errorMessage } from "../../../api/errorMessage";
import { WidgetFrame } from "../../../components/WidgetFrame";

type HubEntry = {
  name: string;
  path: string;
  type: "directory" | "file";
  expandable: boolean;
};

type HubFile = {
  path: string;
  content: string | null;
  state: "text" | "binary" | "unreadable";
};

export function HubExplorerPage() {
  const [directories, setDirectories] = useState<Record<string, HubEntry[]>>(
    {},
  );
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const [file, setFile] = useState<HubFile | null>(null);
  const [loading, setLoading] = useState(true);
  const [fileLoading, setFileLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    requestJson<{ entries: HubEntry[] }>("/api/hub-explorer/directory")
      .then(({ entries }) => setDirectories({ "": entries }))
      .catch((requestError) => setError(errorMessage(requestError)))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!selectedPath) return;
    setFileLoading(true);
    setError(null);
    requestJson<HubFile>(
      `/api/hub-explorer/file?path=${encodeURIComponent(selectedPath)}`,
    )
      .then(setFile)
      .catch((requestError) => setError(errorMessage(requestError)))
      .finally(() => setFileLoading(false));
  }, [selectedPath]);

  const toggleDirectory = (entry: HubEntry) => {
    if (!entry.expandable) return;
    setExpanded((current) => {
      const next = new Set(current);
      next.has(entry.path) ? next.delete(entry.path) : next.add(entry.path);
      return next;
    });
    if (directories[entry.path]) return;
    requestJson<{ entries: HubEntry[] }>(
      `/api/hub-explorer/directory?path=${encodeURIComponent(entry.path)}`,
    )
      .then(({ entries }) =>
        setDirectories((current) => ({ ...current, [entry.path]: entries })),
      )
      .catch((requestError) => setError(errorMessage(requestError)));
  };

  const renderTree = (entries: HubEntry[], depth = 0): ReactNode =>
    entries.map((entry) => {
      const directory = entry.type === "directory";
      const open = expanded.has(entry.path);
      return (
        <Box key={entry.path}>
          <Group
            className="diff-tree-node"
            gap={6}
            onClick={() =>
              directory ? toggleDirectory(entry) : setSelectedPath(entry.path)
            }
            py={3}
            style={{ paddingInlineStart: 8 + depth * 16 }}
            wrap="nowrap"
          >
            {directory && entry.expandable ? (
              <IconChevronRight
                className="diff-tree-chevron"
                data-expanded={open || undefined}
                size={14}
                stroke={1.5}
              />
            ) : (
              <Box w={14} />
            )}
            {directory ? (
              open ? (
                <IconFolderOpen size={15} stroke={1.5} />
              ) : (
                <IconFolder size={15} stroke={1.5} />
              )
            ) : (
              <IconFile
                className="diff-tree-file-icon"
                size={14}
                stroke={1.5}
              />
            )}
            <Text
              data-selected={entry.path === selectedPath || undefined}
              size="sm"
            >
              {entry.name}
            </Text>
          </Group>
          {directory && open && directories[entry.path] && (
            <Box className="diff-tree-children">
              <Box
                className="diff-tree-guide"
                style={{ insetInlineStart: 22 + depth * 16 }}
              />
              {renderTree(directories[entry.path], depth + 1)}
            </Box>
          )}
        </Box>
      );
    });

  return (
    <main className="terminal-page">
      <section className="terminal-diff-layout explorer-page">
        <WidgetFrame title={<Text fw={600}>Explorer</Text>}>
          <ScrollArea h="100%" p="xs">
            {loading ? (
              <Loader m="md" size="sm" />
            ) : (
              renderTree(directories[""] ?? [])
            )}
          </ScrollArea>
        </WidgetFrame>
        <WidgetFrame title={<Text fw={600}>{selectedPath ?? "File"}</Text>}>
          {error ? (
            <Alert color="red" m="md">
              {error}
            </Alert>
          ) : fileLoading ? (
            <Loader m="md" size="sm" />
          ) : !selectedPath ? (
            <Text c="dimmed" p="md">
              ファイルを選択してください。
            </Text>
          ) : file?.state !== "text" ? (
            <Text c="dimmed" p="md">
              {file?.state === "binary"
                ? "バイナリファイルは表示できません。"
                : "ファイルを読み込めません。"}
            </Text>
          ) : (
            <ScrollArea h="100%">
              <Box className="diff-content" component="pre">
                {file.content}
              </Box>
            </ScrollArea>
          )}
        </WidgetFrame>
      </section>
    </main>
  );
}
