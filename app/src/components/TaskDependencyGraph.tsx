import { Box } from "@mantine/core";
import { useEffect, useRef } from "react";
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
  height?: number;
  onSelectTask?: (taskId: string) => void;
};

const GRAPH_PADDING = 24;

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
      const graph = cytoscape({
        container: containerRef.current,
        elements,
        style: [
          {
            selector: "node",
            style: {
              "background-color": "#f8f9fa",
              "border-color": "#868e96",
              "border-width": 2,
              color: "#212529",
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
            style: { "background-color": "#e7f5ff", "border-color": "#228be6" },
          },
          {
            selector: "node.paused",
            style: { "background-color": "#fff3bf", "border-color": "#f08c00" },
          },
          {
            selector: "node.draft",
            style: { "background-color": "#f8f9fa", "border-color": "#868e96" },
          },
          {
            selector: "node.completed",
            style: { "background-color": "#ebfbee", "border-color": "#40c057" },
          },
          {
            selector: "node.cancelled",
            style: {
              "background-color": "#f1f3f5",
              "border-color": "#adb5bd",
              color: "#868e96",
            },
          },
          {
            selector: "edge",
            style: {
              "curve-style": "bezier",
              "line-color": "#adb5bd",
              "target-arrow-color": "#adb5bd",
              "target-arrow-shape": "triangle",
              width: 2,
            },
          },
          {
            selector: "edge.interrupt",
            style: {
              "line-color": "#eca035",
              "line-style": "dashed",
              "target-arrow-color": "#eca035",
              label: "data(label)",
              "font-size": 20,
              color: "#ff8c00",
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
  }, [onSelectTask, tasks]);

  return <Box h={height} ref={containerRef} w="100%" />;
}
