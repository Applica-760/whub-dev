import { Alert, Box, Group, Loader, ScrollArea, Text } from "@mantine/core";
import {
  IconChevronRight,
  IconFile,
  IconFolder,
  IconFolderOpen,
} from "@tabler/icons-react";
import { useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";

import { errorMessage } from "../../api/errorMessage";
import { WidgetFrame } from "../../components/WidgetFrame";
import { fetchChangedFiles, fetchWorktreeDiff } from "./diffApi";
import type { ChangedFile, WorktreeFile } from "./diffApi";

type DiffPaneProps = {
  project: string | undefined;
  taskId: string | undefined;
  workspacePath: string | null | undefined;
};

type ExplorerNode = {
  children: ExplorerNode[];
  label: string;
  path: string;
  status: string;
};

function treeData(files: ChangedFile[]): ExplorerNode[] {
  const root: ExplorerNode[] = [];
  for (const file of files) {
    const parts = file.path.split("/");
    let nodes = root;
    for (const [index, part] of parts.entries()) {
      const existing = nodes.find((node) => node.label === part);
      const node = existing ?? {
        path: parts.slice(0, index + 1).join("/"),
        label: part,
        children: [],
        status: "",
      };
      if (!existing) nodes.push(node);
      if (index === parts.length - 1) node.status = file.status;
      nodes = node.children;
    }
  }
  const sortNodes = (nodes: ExplorerNode[]) => {
    nodes.sort(
      (left, right) =>
        Number(right.children.length > 0) - Number(left.children.length > 0) ||
        left.label.localeCompare(right.label),
    );
    nodes.forEach((node) => sortNodes(node.children));
  };
  sortNodes(root);
  return root;
}

function hasChanges(node: ExplorerNode): boolean {
  return Boolean(node.status) || node.children.some(hasChanges);
}

type RenderedFileLine = {
  content: string;
  kind: "addition" | "context" | "deletion" | "hunk";
  newLine: number | null;
  oldLine: number | null;
  prefix: string;
};

function renderedFileLines(content: string, diff: string): RenderedFileLine[] {
  const insertions = new Map<number, RenderedFileLine[]>();
  const additions = new Set<number>();
  let oldLine = 0;
  let newLine = 0;
  const addInsertion = (line: number, insertion: RenderedFileLine) => {
    insertions.set(line, [...(insertions.get(line) ?? []), insertion]);
  };

  for (const line of diff.split("\n")) {
    const hunk = line.match(/^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@/);
    if (hunk) {
      oldLine = Number(hunk[1]);
      newLine = Number(hunk[2]);
      addInsertion(newLine, {
        content: line,
        kind: "hunk",
        oldLine: null,
        newLine: null,
        prefix: "",
      });
    } else if (line.startsWith("-") && !line.startsWith("---")) {
      addInsertion(newLine, {
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

function changeCount(content: string) {
  return content.split("\n").reduce(
    (count, line) => ({
      added:
        count.added + Number(line.startsWith("+") && !line.startsWith("+++")),
      deleted:
        count.deleted + Number(line.startsWith("-") && !line.startsWith("---")),
    }),
    { added: 0, deleted: 0 },
  );
}

export function DiffPane({ project, taskId, workspacePath }: DiffPaneProps) {
  const [files, setFiles] = useState<ChangedFile[]>([]);
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const [file, setFile] = useState<WorktreeFile | null>(null);
  const [loading, setLoading] = useState(false);
  const [diffLoading, setDiffLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (!project || !taskId) {
      setFiles([]);
      setSelectedPath(null);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetchChangedFiles(project, taskId)
      .then((response) => {
        if (!cancelled) {
          setFiles(response.files);
          setSelectedPath(response.files[0]?.path ?? null);
          setExpanded(new Set());
        }
      })
      .catch(
        (requestError) => !cancelled && setError(errorMessage(requestError)),
      )
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [project, taskId]);

  useEffect(() => {
    if (!project || !taskId || !selectedPath) {
      setFile(null);
      setDiffLoading(false);
      return;
    }
    let cancelled = false;
    setDiffLoading(true);
    setError(null);
    fetchWorktreeDiff(project, taskId, selectedPath)
      .then((response) => !cancelled && setFile(response))
      .catch(
        (requestError) => !cancelled && setError(errorMessage(requestError)),
      )
      .finally(() => !cancelled && setDiffLoading(false));
    return () => {
      cancelled = true;
    };
  }, [project, selectedPath, taskId]);

  const data = useMemo(() => treeData(files), [files]);
  const changes = useMemo(() => changeCount(file?.diff ?? ""), [file]);
  const lines = useMemo(
    () =>
      file?.state === "text" && file.content !== null
        ? renderedFileLines(file.content, file.diff)
        : [],
    [file],
  );
  const copyPath = (path: string) => {
    const relativePath = workspacePath ? `${workspacePath}/${path}` : path;
    void navigator.clipboard?.writeText(relativePath);
  };
  const renderTree = (nodes: ExplorerNode[], depth = 0): ReactNode =>
    nodes.map((node) => {
      const directory = node.children.length > 0;
      const open = expanded.has(node.path);
      const changed = hasChanges(node);
      return (
        <Box key={node.path}>
          <Group
            className="diff-tree-node"
            data-changed={changed || undefined}
            data-new={node.status === "A" || undefined}
            gap={6}
            onClick={() =>
              directory
                ? setExpanded((current) => {
                    const next = new Set(current);
                    next.has(node.path)
                      ? next.delete(node.path)
                      : next.add(node.path);
                    return next;
                  })
                : setSelectedPath(node.path)
            }
            onContextMenu={(event) => {
              event.preventDefault();
              copyPath(node.path);
            }}
            py={3}
            style={{ paddingInlineStart: 8 + depth * 16 }}
            wrap="nowrap"
          >
            {directory ? (
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
              data-selected={node.path === selectedPath || undefined}
              size="sm"
            >
              {node.label}
            </Text>
          </Group>
          {directory && open && (
            <Box className="diff-tree-children">
              <Box
                className="diff-tree-guide"
                style={{ insetInlineStart: 22 + depth * 16 }}
              />
              {renderTree(node.children, depth + 1)}
            </Box>
          )}
        </Box>
      );
    });

  return (
    <section className="terminal-diff-layout">
      <WidgetFrame title={<Text fw={600}>Explorer</Text>}>
        <ScrollArea h="100%" p="xs">
          {loading ? (
            <Loader m="md" size="sm" />
          ) : files.length ? (
            renderTree(data)
          ) : (
            <Text c="dimmed" p="md">
              変更ファイルはありません。
            </Text>
          )}
        </ScrollArea>
      </WidgetFrame>
      <WidgetFrame title={<Text fw={600}>File changes</Text>}>
        {selectedPath && (
          <Group className="diff-meta" gap="xs" px="md" py="sm">
            <Text c="dimmed" size="sm">
              {selectedPath}
            </Text>
            <Text c="green" fw={600} size="sm">
              +{changes.added}
            </Text>
            <Text c="red" fw={600} size="sm">
              -{changes.deleted}
            </Text>
          </Group>
        )}
        {error ? (
          <Alert color="red" m="md">
            {error}
          </Alert>
        ) : diffLoading ? (
          <Loader m="md" size="sm" />
        ) : !selectedPath ? (
          <Text c="dimmed" p="md">
            変更ファイルを選択してください。
          </Text>
        ) : file?.state === "binary" ? (
          <Text c="dimmed" p="md">
            バイナリファイルは表示できません。
          </Text>
        ) : file?.state === "unreadable" ? (
          <Text c="dimmed" p="md">
            ファイルを読み込めません。
          </Text>
        ) : file?.content === "" ? (
          <Text c="dimmed" p="md">
            空のファイルです。
          </Text>
        ) : (
          <ScrollArea h="100%">
            <Box className="diff-content" component="pre">
              {lines.map((line, index) => (
                <div
                  className={`diff-line diff-${line.kind}`}
                  key={`${index}-${line.content}`}
                >
                  <span className="diff-line-number">{line.oldLine ?? ""}</span>
                  <span className="diff-line-number">{line.newLine ?? ""}</span>
                  <span className="diff-line-prefix">{line.prefix}</span>
                  <span className="diff-line-content">
                    {line.content || " "}
                  </span>
                </div>
              ))}
            </Box>
          </ScrollArea>
        )}
      </WidgetFrame>
    </section>
  );
}
