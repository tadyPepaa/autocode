import { useState, useEffect, useRef } from 'react';
import { useParams } from 'react-router-dom';
import { useProject, useUpdateProject, useProjectAction } from '../api/projects';
import Terminal from '../components/Terminal';
import ImplementationPlan from '../components/ImplementationPlan';

type Tab = 'terminal' | 'logs' | 'plan' | 'description' | 'architecture';

interface LogEntry {
  id: number;
  level: string;
  message: string;
  timestamp: string;
}

const statusColors: Record<string, string> = {
  created: 'bg-gray-600',
  running: 'bg-green-600',
  paused: 'bg-yellow-600',
  error: 'bg-red-600',
  completed: 'bg-blue-600',
};

const levelColors: Record<string, string> = {
  debug: 'bg-gray-600',
  info: 'bg-blue-600',
  warning: 'bg-yellow-600',
  error: 'bg-red-600',
};

function LogsPanel({ projectId }: { projectId: number }) {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const ws = new WebSocket(
      `${protocol}//${location.host}/ws/project/${projectId}/logs`,
    );

    ws.onmessage = (e: MessageEvent) => {
      const log = JSON.parse(e.data as string) as LogEntry;
      setLogs((prev) => [...prev, log]);
    };

    return () => ws.close();
  }, [projectId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  if (logs.length === 0) {
    return <p className="text-gray-500 text-sm">No logs yet.</p>;
  }

  return (
    <div className="max-h-[600px] overflow-y-auto rounded-lg bg-gray-900 p-4 space-y-1">
      {logs.map((log) => (
        <div key={log.id} className="flex items-start gap-3 text-sm">
          <span className="shrink-0 text-xs text-gray-500 font-mono w-40">
            {log.timestamp}
          </span>
          <span
            className={`shrink-0 rounded px-1.5 py-0.5 text-xs font-medium text-white ${levelColors[log.level] ?? 'bg-gray-600'}`}
          >
            {log.level}
          </span>
          <span className="text-gray-300">{log.message}</span>
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  );
}

export default function ProjectDetail() {
  const { id } = useParams<{ id: string }>();
  const projectId = Number(id);
  const { data: project, isLoading, isError } = useProject(projectId);
  const updateProject = useUpdateProject();
  const projectAction = useProjectAction();

  const [tab, setTab] = useState<Tab>('terminal');
  const [description, setDescription] = useState<string | null>(null);
  const [architecture, setArchitecture] = useState<string | null>(null);
  const [descSaved, setDescSaved] = useState(false);
  const [archSaved, setArchSaved] = useState(false);

  const currentDesc = description ?? project?.description ?? '';
  const currentArch = architecture ?? project?.architecture ?? '';

  function handleAction(action: 'start' | 'stop' | 'restart') {
    projectAction.mutate({ id: projectId, action });
  }

  function saveDescription() {
    updateProject.mutate(
      { id: projectId, description: currentDesc },
      {
        onSuccess: () => {
          setDescSaved(true);
          setTimeout(() => setDescSaved(false), 2000);
        },
      },
    );
  }

  function saveArchitecture() {
    updateProject.mutate(
      { id: projectId, architecture: currentArch },
      {
        onSuccess: () => {
          setArchSaved(true);
          setTimeout(() => setArchSaved(false), 2000);
        },
      },
    );
  }

  if (isLoading) {
    return (
      <div className="p-6">
        <div className="h-8 w-64 animate-pulse rounded bg-gray-800" />
        <div className="mt-4 h-4 w-32 animate-pulse rounded bg-gray-800" />
      </div>
    );
  }

  if (isError || !project) {
    return (
      <div className="p-6">
        <p className="text-red-400">Project not found.</p>
      </div>
    );
  }

  const tabs: { key: Tab; label: string }[] = [
    { key: 'terminal', label: 'Terminal' },
    { key: 'logs', label: 'Logs' },
    { key: 'plan', label: 'Plan' },
    { key: 'description', label: 'Description' },
    { key: 'architecture', label: 'Architecture' },
  ];

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">{project.name}</h1>
          <div className="mt-1 flex items-center gap-3">
            <span
              className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium text-white ${statusColors[project.status] ?? 'bg-gray-600'}`}
            >
              {project.status}
            </span>
            <span className="text-sm text-gray-500">{project.slug}</span>
          </div>
        </div>

        <div className="flex gap-2">
          {project.status !== 'running' && (
            <button
              onClick={() => handleAction('start')}
              disabled={projectAction.isPending}
              className="rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-green-500 disabled:opacity-50"
            >
              Start
            </button>
          )}
          {project.status === 'running' && (
            <>
              <button
                onClick={() => handleAction('stop')}
                disabled={projectAction.isPending}
                className="rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-red-500 disabled:opacity-50"
              >
                Stop
              </button>
              <button
                onClick={() => handleAction('restart')}
                disabled={projectAction.isPending}
                className="rounded-lg bg-yellow-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-yellow-500 disabled:opacity-50"
              >
                Restart
              </button>
            </>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="mb-6 flex gap-1 rounded-lg bg-gray-800 p-1">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`rounded-md px-4 py-2 text-sm font-medium transition ${
              tab === t.key
                ? 'bg-gray-700 text-white'
                : 'text-gray-400 hover:text-white'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {tab === 'terminal' && (
        <div>
          {project.status === 'running' ? (
            <Terminal projectId={projectId} />
          ) : (
            <div className="rounded-lg bg-gray-800 p-8 text-center">
              <p className="text-gray-400">
                Start the project to see the terminal.
              </p>
            </div>
          )}
        </div>
      )}

      {tab === 'logs' && <LogsPanel projectId={projectId} />}

      {tab === 'plan' && (
        <ImplementationPlan
          planJson={project.implementation_plan}
          currentStep={project.current_step}
        />
      )}

      {tab === 'description' && (
        <div>
          <textarea
            value={currentDesc}
            onChange={(e) => {
              setDescription(e.target.value);
              setDescSaved(false);
            }}
            rows={12}
            className="w-full rounded-lg border border-gray-600 bg-gray-800 px-4 py-3 text-sm text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            placeholder="Project description..."
          />
          <div className="mt-2 flex items-center gap-3">
            <button
              onClick={saveDescription}
              disabled={updateProject.isPending}
              className="rounded-lg bg-blue-600 px-4 py-1.5 text-sm font-medium text-white transition hover:bg-blue-500 disabled:opacity-50"
            >
              {updateProject.isPending ? 'Saving...' : 'Save'}
            </button>
            {descSaved && (
              <span className="text-sm text-green-400">Saved</span>
            )}
          </div>
        </div>
      )}

      {tab === 'architecture' && (
        <div>
          <textarea
            value={currentArch}
            onChange={(e) => {
              setArchitecture(e.target.value);
              setArchSaved(false);
            }}
            rows={12}
            className="w-full rounded-lg border border-gray-600 bg-gray-800 px-4 py-3 text-sm text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            placeholder="Architecture notes..."
          />
          <div className="mt-2 flex items-center gap-3">
            <button
              onClick={saveArchitecture}
              disabled={updateProject.isPending}
              className="rounded-lg bg-blue-600 px-4 py-1.5 text-sm font-medium text-white transition hover:bg-blue-500 disabled:opacity-50"
            >
              {updateProject.isPending ? 'Saving...' : 'Save'}
            </button>
            {archSaved && (
              <span className="text-sm text-green-400">Saved</span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
