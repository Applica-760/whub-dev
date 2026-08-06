import { Box, useComputedColorScheme } from "@mantine/core";
import { useEffect, useRef } from "react";
import type { CSSProperties } from "react";
import type { ElementDefinition, LayoutOptions } from "cytoscape";

export type TaskGraphItem = {
  id?: string | null;
  title?: string | null;
  state?: string | null;
  depends_on?: string[];
  interruption_source_task_id?: string | null;
};

type TaskDependencyGraphProps = {
  tasks: TaskGraphItem[];
  height?: CSSProperties["height"];
  onSelectTask?: (taskId: string) => void;
};

const GRAPH_PADDING = 24;

const GRAPH_COLOR_VARIABLES = {
  nodeBackground: "--whub-color-task-graph-node-background",
  nodeBorder: "--whub-color-task-graph-node-border",
  nodeText: "--whub-color-task-graph-node-text",
  inProgressBackground: "--whub-color-task-graph-in-progress-background",
  inProgressBorder: "--whub-color-task-graph-in-progress-border",
  pausedBackground: "--whub-color-task-graph-paused-background",
  pausedBorder: "--whub-color-task-graph-paused-border",
  completedBackground: "--whub-color-task-graph-completed-background",
  completedBorder: "--whub-color-task-graph-completed-border",
  cancelledBackground: "--whub-color-task-graph-cancelled-background",
  cancelledBorder: "--whub-color-task-graph-cancelled-border",
  cancelledText: "--whub-color-task-graph-cancelled-text",
  edge: "--whub-color-task-graph-edge",
  interrupt: "--whub-color-task-graph-interrupt",
} as const;

function graphColors(element: HTMLElement) {
  const styles = getComputedStyle(element);
  return Object.fromEntries(
    Object.entries(GRAPH_COLOR_VARIABLES).map(([name, variable]) => [
      name,
      styles.getPropertyValue(variable).trim(),
    ]),
  ) as Record<keyof typeof GRAPH_COLOR_VARIABLES, string>;
}

export function buildTaskGraphElements(
  tasks: TaskGraphItem[],
): ElementDefinition[] {
  const identifiedTasks = tasks.filter(
    (task): task is TaskGraphItem & { id: string } => Boolean(task.id),
  );
  const tasksById = new Map(identifiedTasks.map((task) => [task.id, task]));
  const interruptingTasks = new Map<string, string[]>();
  identifiedTasks.forEach((task) => {
    if (task.interruption_source_task_id != null) {
      const sources =
        interruptingTasks.get(task.interruption_source_task_id) ?? [];
      sources.push(task.id);
      interruptingTasks.set(task.interruption_source_task_id, sources);
    }
  });

  const visibleIds = new Set(
    identifiedTasks
      .filter(
        (task) => task.state !== "completed" && task.state !== "cancelled",
      )
      .map((task) => task.id),
  );
  const pending = [...visibleIds];
  while (pending.length > 0) {
    const taskId = pending.pop();
    if (taskId == null) {
      continue;
    }
    const task = tasksById.get(taskId);
    const upstreamIds = [
      ...(task?.depends_on ?? []),
      ...(interruptingTasks.get(taskId) ?? []),
    ];
    upstreamIds.forEach((upstreamId) => {
      if (tasksById.has(upstreamId) && !visibleIds.has(upstreamId)) {
        visibleIds.add(upstreamId);
        pending.push(upstreamId);
      }
    });
  }

  const visibleTasks = identifiedTasks.filter((task) =>
    visibleIds.has(task.id),
  );
  const taskIds = new Set(visibleTasks.map((task) => task.id));

  return [
    ...visibleTasks.map((task) => ({
      data: {
        id: task.id,
        label: `${task.id}\n${task.title ?? task.id}`,
      },
      classes: task.state ?? "invalid",
    })),
    ...visibleTasks.flatMap((task) =>
      (task.depends_on ?? [])
        .filter((dependency) => taskIds.has(dependency))
        .map((dependency) => ({
          data: {
            id: `dependency-${dependency}-${task.id}`,
            source: dependency,
            target: task.id,
          },
        })),
    ),
    ...visibleTasks.flatMap((task) =>
      task.interruption_source_task_id != null &&
      taskIds.has(task.interruption_source_task_id)
        ? [
            {
              data: {
                id: `interrupt-${task.interruption_source_task_id}-${task.id}`,
                source: task.id,
                target: task.interruption_source_task_id,
                label: "interrupt",
              },
              classes: "interrupt",
            },
          ]
        : [],
    ),
  ];
}

export function TaskDependencyGraph({
  tasks,
  height = 360,
  onSelectTask,
}: TaskDependencyGraphProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const colorScheme = useComputedColorScheme("light");

  useEffect(() => {
    let cancelled = false;
    let destroy: (() => void) | undefined;

    async function render() {
      if (!containerRef.current) {
        return;
      }
      const [{ default: cytoscape }, { default: fcose }] = await Promise.all([
        import("cytoscape"),
        import("cytoscape-fcose"),
      ]);
      if (cancelled || !containerRef.current) {
        return;
      }
      cytoscape.use(fcose);

      const elements = buildTaskGraphElements(tasks);
      const colors = graphColors(containerRef.current);
      const graph = cytoscape({
        container: containerRef.current,
        elements,
        style: [
          {
            selector: "node",
            style: {
              "background-color": colors.nodeBackground,
              "border-color": colors.nodeBorder,
              "border-width": 2,
              color: colors.nodeText,
              "font-size": 14,
              height: "96px",
              label: "data(label)",
              "line-height": 1.35,
              "text-halign": "center",
              "text-justification": "center",
              "text-max-width": "190px",
              "text-overflow-wrap": "anywhere",
              "text-valign": "center",
              "text-wrap": "wrap",
              width: "220px",
            },
          },
          {
            selector: "node.in_progress",
            style: {
              "background-color": colors.inProgressBackground,
              "border-color": colors.inProgressBorder,
            },
          },
          {
            selector: "node.paused",
            style: {
              "background-color": colors.pausedBackground,
              "border-color": colors.pausedBorder,
            },
          },
          {
            selector: "node.draft",
            style: {
              "background-color": colors.nodeBackground,
              "border-color": colors.nodeBorder,
            },
          },
          {
            selector: "node.completed",
            style: {
              "background-color": colors.completedBackground,
              "border-color": colors.completedBorder,
            },
          },
          {
            selector: "node.cancelled",
            style: {
              "background-color": colors.cancelledBackground,
              "border-color": colors.cancelledBorder,
              color: colors.cancelledText,
            },
          },
          {
            selector: "edge",
            style: {
              "curve-style": "bezier",
              "line-color": colors.edge,
              "target-arrow-color": colors.edge,
              "target-arrow-shape": "triangle",
              width: 2,
            },
          },
          {
            selector: "edge.interrupt",
            style: {
              "line-color": colors.interrupt,
              "line-style": "dashed",
              "target-arrow-color": colors.interrupt,
              label: "data(label)",
              "font-size": 20,
              color: colors.interrupt,
            },
          },
        ],
        layout: {
          animate: false,
          fit: true,
          idealEdgeLength: 180,
          name: "fcose",
          nodeDimensionsIncludeLabels: true,
          nodeRepulsion: 6500,
          padding: GRAPH_PADDING,
        } as LayoutOptions,
        wheelSensitivity: 0.2,
      });
      if (onSelectTask) {
        graph.on("tap", "node", (event) => {
          onSelectTask(event.target.id());
        });
      }

      // cytoscapeはwindow resizeしか拾わないため、列の折りたたみによる幅変化を自前で追従する
      const observer = new ResizeObserver(([entry]) => {
        const { width, height: observedHeight } = entry.contentRect;
        if (width === 0 || observedHeight === 0) {
          return;
        }
        graph.resize();
        graph.fit(undefined, GRAPH_PADDING);
      });
      observer.observe(containerRef.current);

      destroy = () => {
        observer.disconnect();
        graph.destroy();
      };
    }

    void render();
    return () => {
      cancelled = true;
      destroy?.();
    };
  }, [colorScheme, onSelectTask, tasks]);

  return <Box h={height} ref={containerRef} w="100%" />;
}
