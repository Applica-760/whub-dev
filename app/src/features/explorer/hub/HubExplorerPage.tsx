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
import { TerminalWidgetFrame } from "../../../components/TerminalWidgetFrame";
import { FileTabs } from "../FileTabs";
import { highlightLine } from "../fileLanguage";

type HubEntry = {
  name: string;
  path: string;
  type: "directory" | "file";
  expandable: boolean;
  changed: boolean;
};

type HubFile = {
  path: string;
  content: string | null;
  state: "text" | "binary" | "unreadable";
  diff: string;
};

type RenderedFileLine = {
  content: string;
  kind: "addition" | "context" | "deletion" | "hunk";
  newLine: number | null;
  oldLine: number | null;
  prefix: string;
};

const EXPLORER_STATE_KEY = "whub.hub-explorer";

function restoredState() {
  try {
    const value = JSON.parse(localStorage.getItem(EXPLORER_STATE_KEY) ?? "{}");
    return {
      expanded: new Set<string>(value.expanded ?? []),
      recentPaths: Array.isArray(value.recentPaths) ? value.recentPaths : [],
      selectedPath:
        typeof value.selectedPath === "string" ? value.selectedPath : null,
    };
  } catch {
    return { expanded: new Set<string>(), recentPaths: [], selectedPath: null };
  }
}

function renderedFileLines(content: string, diff: string): RenderedFileLine[] {
  const insertions = new Map<number, RenderedFileLine[]>();
  const additions = new Set<number>();
  let oldLine = 0;
  let newLine = 0;
  const insert = (line: number, item: RenderedFileLine) => {
    insertions.set(line, [...(insertions.get(line) ?? []), item]);
  };
  for (const line of diff.split("\n")) {
    const hunk = line.match(/^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@/);
    if (hunk) {
      oldLine = Number(hunk[1]);
      newLine = Number(hunk[2]);
      insert(newLine, {
        content: line,
        kind: "hunk",
        oldLine: null,
        newLine: null,
        prefix: "",
      });
    } else if (line.startsWith("-") && !line.startsWith("---")) {
      insert(newLine, {
        content: line.slice(1),
        kind: "deletion",
        oldLine: oldLine++,
        newLine: null,
        prefix: "-",
      });
    } else if (line.startsWith("+") && !line.startsWith("+++")) {
      additions.add(newLine++);
    } else if (line.startsWith(" ")) {
      oldLine++;
      newLine++;
    }
  }
  const lines = content.split("\n");
  if (lines.at(-1) === "") lines.pop();
  return lines
    .flatMap((line, index): RenderedFileLine[] => [
      ...(insertions.get(index + 1) ?? []),
      {
        content: line,
        kind: additions.has(index + 1) ? "addition" : "context",
        oldLine: null,
        newLine: index + 1,
        prefix: additions.has(index + 1) ? "+" : " ",
      },
    ])
    .concat(insertions.get(lines.length + 1) ?? []);
}

export function HubExplorerPage() {
  const initial = restoredState();
  const [directories, setDirectories] = useState<Record<string, HubEntry[]>>(
    {},
  );
  const [expanded, setExpanded] = useState<Set<string>>(initial.expanded);
  const [selectedPath, setSelectedPath] = useState<string | null>(
    initial.selectedPath,
  );
  const [recentPaths, setRecentPaths] = useState<string[]>(initial.recentPaths);
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
    for (const path of expanded) {
      requestJson<{ entries: HubEntry[] }>(
        `/api/hub-explorer/directory?path=${encodeURIComponent(path)}`,
      ).then(({ entries }) =>
        setDirectories((current) => ({ ...current, [path]: entries })),
      );
    }
  }, []);

  useEffect(() => {
    localStorage.setItem(
      EXPLORER_STATE_KEY,
      JSON.stringify({
        expanded: [...expanded],
        recentPaths,
        selectedPath,
      }),
    );
  }, [expanded, recentPaths, selectedPath]);

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

  const selectFile = (path: string) => {
    setSelectedPath(path);
    setRecentPaths((current) =>
      current.includes(path) ? current : [...current, path].slice(-8),
    );
  };
  const closeFile = (path: string) => {
    setRecentPaths((current) => current.filter((item) => item !== path));
    if (selectedPath === path) {
      setSelectedPath(
        recentPaths.filter((item) => item !== path).at(-1) ?? null,
      );
    }
  };
  const lines =
    file?.state === "text" && file.content !== null
      ? renderedFileLines(file.content, file.diff)
      : [];

  const renderTree = (entries: HubEntry[], depth = 0): ReactNode =>
    entries.map((entry) => {
      const directory = entry.type === "directory";
      const open = expanded.has(entry.path);
      return (
        <Box key={entry.path}>
          <Group
            className="diff-tree-node"
            data-changed={entry.changed || undefined}
            gap={6}
            onClick={() =>
              directory ? toggleDirectory(entry) : selectFile(entry.path)
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
        <TerminalWidgetFrame>
          <ScrollArea h="100%" p="xs">
            {loading ? (
              <Loader m="md" size="sm" />
            ) : (
              renderTree(directories[""] ?? [])
            )}
          </ScrollArea>
        </TerminalWidgetFrame>
        <TerminalWidgetFrame>
          <div className="explorer-file">
            <FileTabs
              onClose={closeFile}
              onSelect={selectFile}
              paths={recentPaths}
              selectedPath={selectedPath}
            />
            <div className="explorer-file-body">
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
                    {lines.map((line, index) => (
                      <div
                        className={`diff-line diff-${line.kind}`}
                        key={`${index}-${line.content}`}
                      >
                        <span className="diff-line-number">
                          {line.oldLine ?? ""}
                        </span>
                        <span className="diff-line-number">
                          {line.newLine ?? ""}
                        </span>
                        <span className="diff-line-prefix">{line.prefix}</span>
                        <span
                          className="diff-line-content"
                          dangerouslySetInnerHTML={{
                            __html: highlightLine(
                              line.content || " ",
                              selectedPath,
                            ),
                          }}
                        />
                      </div>
                    ))}
                  </Box>
                </ScrollArea>
              )}
            </div>
          </div>
        </TerminalWidgetFrame>
      </section>
    </main>
  );
}
