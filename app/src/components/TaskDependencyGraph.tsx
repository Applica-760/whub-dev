import { Box } from '@mantine/core';
import { useEffect, useRef } from 'react';
import type { ElementDefinition, LayoutOptions } from 'cytoscape';
import { useNavigate } from 'react-router';

type TaskGraphItem = {
  id?: string | null;
  title?: string | null;
  state?: string | null;
  depends_on?: string[];
  interruption_source_task_id?: string | null;
};

type TaskDependencyGraphProps = {
  tasks: TaskGraphItem[];
  height?: number;
};

export function TaskDependencyGraph({ tasks, height = 360 }: TaskDependencyGraphProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  useEffect(() => {
    let cancelled = false;
    let destroy: (() => void) | undefined;

    async function render() {
      if (!containerRef.current) {
        return;
      }
      const [{ default: cytoscape }, { default: fcose }] = await Promise.all([
        import('cytoscape'),
        import('cytoscape-fcose'),
      ]);
      if (cancelled || !containerRef.current) {
        return;
      }
      cytoscape.use(fcose);

      const visibleTasks = tasks.filter(
        (task): task is TaskGraphItem & { id: string } => Boolean(task.id)
          && (task.state !== 'completed' || task.interruption_source_task_id != null),
      );
      const taskIds = new Set(visibleTasks.map((task) => task.id));
      const elements: ElementDefinition[] = [
        ...visibleTasks.map((task) => ({
          data: {
            id: task.id,
            label: `${task.id}\n${task.title ?? task.id}`,
          },
          classes: task.state ?? 'invalid',
        })),
        ...visibleTasks.flatMap((task) => (task.depends_on ?? [])
          .filter((dependency) => taskIds.has(dependency))
          .map((dependency) => ({
            data: { id: `dependency-${dependency}-${task.id}`, source: dependency, target: task.id },
          }))),
        ...visibleTasks.flatMap((task) => (task.interruption_source_task_id != null
          && taskIds.has(task.interruption_source_task_id)
          ? [{
            data: {
              id: `interrupt-${task.interruption_source_task_id}-${task.id}`,
              source: task.id,
              target: task.interruption_source_task_id,
              label: 'interrupt',
            },
            classes: 'interrupt',
          }]
          : [])),
      ];
      const graph = cytoscape({
        container: containerRef.current,
        elements,
        style: [
          {
            selector: 'node',
            style: {
              'background-color': '#f8f9fa',
              'border-color': '#868e96',
              'border-width': 2,
              color: '#212529',
              height: '96px',
              label: 'data(label)',
              'line-height': 1.35,
              'text-halign': 'center',
              'text-justification': 'center',
              'text-max-width': '190px',
              'text-overflow-wrap': 'anywhere',
              'text-valign': 'center',
              'text-wrap': 'wrap',
              width: '220px',
            },
          },
          { selector: 'node.in_progress', style: { 'background-color': '#e7f5ff', 'border-color': '#228be6' } },
          { selector: 'node.paused', style: { 'background-color': '#fff3bf', 'border-color': '#f08c00' } },
          { selector: 'node.draft', style: { 'background-color': '#f8f9fa', 'border-color': '#868e96' } },
          {
            selector: 'edge',
            style: {
              'curve-style': 'bezier',
              'line-color': '#adb5bd',
              'target-arrow-color': '#adb5bd',
              'target-arrow-shape': 'triangle',
              width: 2,
            },
          },
          {
            selector: 'edge.interrupt',
            style: {
              'line-color': '#eca035',
              'line-style': 'dashed',
              'target-arrow-color': '#eca035',
              label: 'data(label)',
              'font-size': 20,
              color: '#ff8c00',
            },
          },
        ],
        layout: {
          animate: false,
          fit: true,
          idealEdgeLength: 180,
          name: 'fcose',
          nodeDimensionsIncludeLabels: true,
          nodeRepulsion: 6500,
          padding: 24,
        } as LayoutOptions,
        wheelSensitivity: 0.2,
      });
      graph.on('tap', 'node', (event) => {
        navigate(`/tasks/${event.target.id()}`);
      });
      destroy = () => graph.destroy();
    }

    void render();
    return () => {
      cancelled = true;
      destroy?.();
    };
  }, [navigate, tasks]);

  return <Box h={height} ref={containerRef} w="100%" />;
}
