import { Alert, Box } from '@mantine/core';
import { useEffect, useRef, useState } from 'react';

let diagramNumber = 0;
let initialized = false;

async function loadMermaid() {
  const { default: mermaid } = await import('mermaid');
  if (!initialized) {
    mermaid.initialize({ securityLevel: 'strict', startOnLoad: false });
    initialized = true;
  }
  return mermaid;
}

type MermaidDiagramProps = {
  chart: string;
};

export function MermaidDiagram({ chart }: MermaidDiagramProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const idRef = useRef(`mermaid-diagram-${diagramNumber += 1}`);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function render() {
      if (!containerRef.current) {
        return;
      }
      try {
        const mermaid = await loadMermaid();
        const result = await mermaid.render(idRef.current, chart);
        if (cancelled || !containerRef.current) {
          return;
        }
        containerRef.current.innerHTML = result.svg;
        result.bindFunctions?.(containerRef.current);
        setError(null);
      } catch (renderError) {
        if (!cancelled) {
          setError(renderError instanceof Error ? renderError.message : 'Mermaidを描画できませんでした');
        }
      }
    }

    void render();
    return () => {
      cancelled = true;
    };
  }, [chart]);

  if (error) {
    return <Alert color="red" title="図を描画できませんでした">{error}</Alert>;
  }
  return <Box ref={containerRef} />;
}
