import { Box } from "@mantine/core";
import { useEffect, useRef } from "react";
import type { ElementDefinition, LayoutOptions } from "cytoscape";

export type TaskGraphItem = {
  id?: string | null;
  project: string;
  title?: string | null;
  state?: string | null;
  depends_on?: string[];
  interruption_source_task_id?: string | null;
};

type TaskDependencyGraphProps = {
  tasks: TaskGraphItem[];
  height?: number;
  onSelectTask?: (project: string, taskId: string) => void;
};

const GRAPH_PADDING = 24;

// Task IDはProject内で採番されるため、Projectを冠してnode idの衝突を防ぐ
function nodeId(project: string, taskId: string): string {
  return `${project}/${taskId}`;
}

export function buildTaskGraphElements(
  tasks: TaskGraphItem[],
): ElementDefinition[] {
  const identifiedTasks = tasks.filter(
    (task): task is TaskGraphItem & { id: string } => Boolean(task.id),
  );
  const tasksByNodeId = new Map(
    identifiedTasks.map((task) => [nodeId(task.project, task.id), task]),
  );
  const interruptingNodeIds = new Map<string, string[]>();
  identifiedTasks.forEach((task) => {
    if (task.interruption_source_task_id != null) {
      const sourceNodeId = nodeId(
        task.project,
        task.interruption_source_task_id,
      );
      const sources = interruptingNodeIds.get(sourceNodeId) ?? [];
      sources.push(nodeId(task.project, task.id));
      interruptingNodeIds.set(sourceNodeId, sources);
    }
  });

  const visibleNodeIds = new Set(
    identifiedTasks
      .filter(
        (task) => task.state !== "completed" && task.state !== "cancelled",
      )
      .map((task) => nodeId(task.project, task.id)),
  );
  const pending = [...visibleNodeIds];
  while (pending.length > 0) {
    const currentNodeId = pending.pop();
    if (currentNodeId == null) {
      continue;
    }
    const task = tasksByNodeId.get(currentNodeId);
    // 依存も割り込みも同一Project内でのみ解決し、Project跨ぎの誤結線を防ぐ
    const upstreamNodeIds = [
      ...(task ? (task.depends_on ?? []) : []).map((dependency) =>
        nodeId(task?.project ?? "", dependency),
      ),
      ...(interruptingNodeIds.get(currentNodeId) ?? []),
    ];
    upstreamNodeIds.forEach((upstreamNodeId) => {
      if (
        tasksByNodeId.has(upstreamNodeId) &&
        !visibleNodeIds.has(upstreamNodeId)
      ) {
        visibleNodeIds.add(upstreamNodeId);
        pending.push(upstreamNodeId);
      }
    });
  }

  const visibleTasks = identifiedTasks.filter((task) =>
    visibleNodeIds.has(nodeId(task.project, task.id)),
  );
  const visibleProjects = [...new Set(visibleTasks.map((task) => task.project))];

  return [
    ...visibleProjects.map((project) => ({
      data: { id: project },
      classes: "project",
    })),
    ...visibleTasks.map((task) => ({
      data: {
        id: nodeId(task.project, task.id),
        label: `${task.project}:${task.id}\n${task.title ?? task.id}`,
        parent: task.project,
        project: task.project,
        taskId: task.id,
      },
      classes: task.state ?? "invalid",
    })),
    ...visibleTasks.flatMap((task) =>
      (task.depends_on ?? [])
        .map((dependency) => nodeId(task.project, dependency))
        .filter((dependencyNodeId) => visibleNodeIds.has(dependencyNodeId))
        .map((dependencyNodeId) => ({
          data: {
            id: `dependency-${dependencyNodeId}-${nodeId(task.project, task.id)}`,
            source: dependencyNodeId,
            target: nodeId(task.project, task.id),
          },
        })),
    ),
    ...visibleTasks.flatMap((task) => {
      if (task.interruption_source_task_id == null) {
        return [];
      }
      const sourceNodeId = nodeId(
        task.project,
        task.interruption_source_task_id,
      );
      if (!visibleNodeIds.has(sourceNodeId)) {
        return [];
      }
      return [
        {
          data: {
            id: `interrupt-${sourceNodeId}-${nodeId(task.project, task.id)}`,
            source: nodeId(task.project, task.id),
            target: sourceNodeId,
            label: "interrupt",
          },
          classes: "interrupt",
        },
      ];
    }),
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
            // Project枠が固定寸法へ潰れないよう、Taskノードだけに寸法を与える
            selector: "node:childless",
            style: {
              "background-color": "#f8f9fa",
              "border-color": "#868e96",
              "border-width": 2,
              color: "#212529",
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
            // Project枠は薄い枠だけにし、Project名はTaskノードのラベルで示す
            selector: ":parent",
            style: {
              "background-opacity": 0,
              "border-color": "#dee2e6",
              "border-width": 1,
              label: "",
              padding: "16px",
              shape: "round-rectangle",
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
          const { project, taskId } = event.target.data();
          // Project枠のノードは選択対象にしない
          if (project && taskId) {
            onSelectTask(project, taskId);
          }
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
