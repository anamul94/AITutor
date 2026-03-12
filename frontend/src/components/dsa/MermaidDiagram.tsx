'use client';

import { useEffect, useId, useState } from 'react';

interface Props {
  code: string;
}

export default function MermaidDiagram({ code }: Props) {
  const rawId = useId();
  // useId returns values like ":r0:" — strip colons so they're valid HTML ids
  const id = `mermaid-${rawId.replace(/:/g, '')}`;
  const [svg, setSvg] = useState<string>('');
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const { default: mermaid } = await import('mermaid');
        mermaid.initialize({
          startOnLoad: false,
          theme: 'base',
          themeVariables: {
            background: '#0d1117',
            primaryColor: '#1e3a5f',
            primaryTextColor: '#e2e8f0',
            primaryBorderColor: '#2d3a4e',
            lineColor: '#64748b',
            secondaryColor: '#162032',
            tertiaryColor: '#0f1c2e',
            edgeLabelBackground: '#111a26',
            nodeTextColor: '#e2e8f0',
          },
        });
        const { svg: rendered } = await mermaid.render(id, code.trim());
        if (!cancelled) setSvg(rendered);
      } catch {
        if (!cancelled) setError(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [code, id]);

  if (error) {
    return (
      <pre className="my-2 overflow-x-auto rounded-lg border border-gray-700 bg-gray-900/50 p-3 text-xs text-gray-400">
        {code}
      </pre>
    );
  }

  if (!svg) {
    return (
      <div className="my-2 h-24 animate-pulse rounded-lg border border-[#1f232b] bg-gray-800/40" />
    );
  }

  return (
    <div
      className="my-3 overflow-x-auto rounded-lg border border-[#2d3a4e] bg-[#0d1117] p-4 [&_svg]:max-w-full"
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  );
}
