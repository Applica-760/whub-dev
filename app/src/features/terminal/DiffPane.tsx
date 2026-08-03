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
import type { ChangedFile } from "./diffApi";

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
  return root;
}

function hasChanges(node: ExplorerNode): boolean {
  return Boolean(node.status) || node.children.some(hasChanges);
}

type RenderedDiffLine = {
  content: string;
  kind: "addition" | "context" | "deletion" | "file" | "hunk";
  newLine: number | null;
  oldLine: number | null;
  prefix: string;
};

function renderedDiffLines(content: string): RenderedDiffLine[] {
  let oldLine = 0;
  let newLine = 0;
  return content.split("\n").map((line) => {
    const hunk = line.match(/^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@/);
    if (hunk) {
      oldLine = Number(hunk[1]);
      newLine = Number(hunk[2]);
      return {
        content: line,
        kind: "hunk",
        oldLine: null,
        newLine: null,
        prefix: "",
      };
    }
    if (line.startsWith("+++") || line.startsWith("---"))
      return {
        content: line,
        kind: "file",
        oldLine: null,
        newLine: null,
        prefix: "",
      };
    if (line.startsWith("+") && !line.startsWith("+++"))
      return {
        content: line.slice(1),
        kind: "addition",
        oldLine: null,
        newLine: newLine++,
        prefix: "+",
      };
    if (line.startsWith("-") && !line.startsWith("---"))
      return {
        content: line.slice(1),
        kind: "deletion",
        oldLine: oldLine++,
        newLine: null,
        prefix: "-",
      };
    if (line.startsWith(" "))
      return {
        content: line.slice(1),
        kind: "context",
        oldLine: oldLine++,
        newLine: newLine++,
        prefix: " ",
      };
    return {
      content: line,
      kind: "context",
      oldLine: null,
      newLine: null,
      prefix: "",
    };
  });
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
  const [content, setContent] = useState("");
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
      setContent("");
      setDiffLoading(false);
      return;
    }
    let cancelled = false;
    setDiffLoading(true);
    setError(null);
    fetchWorktreeDiff(project, taskId, selectedPath)
      .then((response) => !cancelled && setContent(response.content))
      .catch(
        (requestError) => !cancelled && setError(errorMessage(requestError)),
      )
      .finally(() => !cancelled && setDiffLoading(false));
    return () => {
      cancelled = true;
    };
  }, [project, selectedPath, taskId]);

  const data = useMemo(() => treeData(files), [files]);
  const changes = useMemo(() => changeCount(content), [content]);
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
          {directory && open && renderTree(node.children ?? [], depth + 1)}
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
        ) : (
          <ScrollArea h="100%">
            <Box className="diff-content" component="pre">
              {renderedDiffLines(content).map((line, index) => (
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
