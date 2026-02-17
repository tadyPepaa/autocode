import { useEffect, useRef } from 'react';
import { Terminal as XTerm } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import '@xterm/xterm/css/xterm.css';

export default function Terminal({ projectId }: { projectId: number }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!ref.current) return;

    const term = new XTerm({
      theme: {
        background: '#1a1a2e',
        foreground: '#e0e0e0',
      },
      fontSize: 14,
      fontFamily: 'monospace',
    });
    const fit = new FitAddon();
    term.loadAddon(fit);
    term.open(ref.current);
    fit.fit();

    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const ws = new WebSocket(
      `${protocol}//${location.host}/ws/project/${projectId}/terminal`,
    );

    ws.onmessage = (e: MessageEvent) => {
      term.clear();
      term.write(e.data as string);
    };

    const container = ref.current;
    const resizeObserver = new ResizeObserver(() => fit.fit());
    resizeObserver.observe(container);

    return () => {
      resizeObserver.disconnect();
      ws.close();
      term.dispose();
    };
  }, [projectId]);

  return (
    <div ref={ref} className="h-[600px] w-full rounded-lg overflow-hidden" />
  );
}
