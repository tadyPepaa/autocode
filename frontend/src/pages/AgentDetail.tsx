import { useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useAgent, useUpdateAgent } from '../api/agents';
import { useProjects, useCreateProject, type Project } from '../api/projects';

const statusColors: Record<string, string> = {
  created: 'bg-gray-600',
  running: 'bg-green-600',
  paused: 'bg-yellow-600',
  error: 'bg-red-600',
  completed: 'bg-blue-600',
};

function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium text-white ${statusColors[status] ?? 'bg-gray-600'}`}
    >
      {status}
    </span>
  );
}

function CodingAgentView({ agentId }: { agentId: number }) {
  const { data: agent } = useAgent(agentId);
  const updateAgent = useUpdateAgent();
  const { data: projects, isLoading: projectsLoading } = useProjects(agentId);
  const createProject = useCreateProject(agentId);
  const navigate = useNavigate();

  const [globalRules, setGlobalRules] = useState<string | null>(null);
  const [rulesSaved, setRulesSaved] = useState(false);

  const [showModal, setShowModal] = useState(false);
  const [newProject, setNewProject] = useState({
    name: '',
    description: '',
    architecture: '',
  });
  const [createError, setCreateError] = useState('');

  // Initialize globalRules from agent data once loaded
  const currentRules = globalRules ?? agent?.global_rules ?? '';

  function handleSaveRules() {
    if (!agent) return;
    updateAgent.mutate(
      { id: agent.id, global_rules: currentRules },
      {
        onSuccess: () => {
          setRulesSaved(true);
          setTimeout(() => setRulesSaved(false), 2000);
        },
      },
    );
  }

  async function handleCreateProject(e: React.FormEvent) {
    e.preventDefault();
    setCreateError('');
    if (!newProject.name.trim()) {
      setCreateError('Name is required.');
      return;
    }
    try {
      const created = (await createProject.mutateAsync({
        name: newProject.name.trim(),
        description: newProject.description,
        architecture: newProject.architecture || undefined,
      })) as Project;
      setShowModal(false);
      setNewProject({ name: '', description: '', architecture: '' });
      navigate(`/projects/${created.id}`);
    } catch {
      setCreateError('Failed to create project.');
    }
  }

  return (
    <>
      {/* Global Rules */}
      <section className="mb-8">
        <h2 className="mb-3 text-lg font-semibold text-gray-300">
          Global Rules
        </h2>
        <textarea
          value={currentRules}
          onChange={(e) => {
            setGlobalRules(e.target.value);
            setRulesSaved(false);
          }}
          rows={6}
          className="w-full rounded-lg border border-gray-600 bg-gray-800 px-4 py-2 text-sm text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          placeholder="Rules the agent must always follow..."
        />
        <div className="mt-2 flex items-center gap-3">
          <button
            onClick={handleSaveRules}
            disabled={updateAgent.isPending}
            className="rounded-lg bg-blue-600 px-4 py-1.5 text-sm font-medium text-white transition hover:bg-blue-500 disabled:opacity-50"
          >
            {updateAgent.isPending ? 'Saving...' : 'Save Rules'}
          </button>
          {rulesSaved && (
            <span className="text-sm text-green-400">Saved</span>
          )}
        </div>
      </section>

      {/* Projects */}
      <section>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-300">Projects</h2>
          <button
            onClick={() => setShowModal(true)}
            className="rounded-lg bg-blue-600 px-4 py-1.5 text-sm font-medium text-white transition hover:bg-blue-500"
          >
            + New Project
          </button>
        </div>

        {projectsLoading && (
          <div className="space-y-2">
            {Array.from({ length: 3 }).map((_, i) => (
              <div
                key={i}
                className="h-12 animate-pulse rounded-lg bg-gray-800"
              />
            ))}
          </div>
        )}

        {!projectsLoading && projects && projects.length === 0 && (
          <p className="text-gray-500">
            No projects yet. Create your first project.
          </p>
        )}

        {!projectsLoading && projects && projects.length > 0 && (
          <div className="overflow-hidden rounded-lg border border-gray-700">
            <table className="w-full text-left text-sm">
              <thead className="bg-gray-800 text-gray-400">
                <tr>
                  <th className="px-4 py-3 font-medium">Name</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  <th className="px-4 py-3 font-medium">Step</th>
                  <th className="px-4 py-3 font-medium" />
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-700">
                {projects.map((project) => (
                  <tr key={project.id} className="hover:bg-gray-800/50">
                    <td className="px-4 py-3 text-white">{project.name}</td>
                    <td className="px-4 py-3">
                      <StatusBadge status={project.status} />
                    </td>
                    <td className="px-4 py-3 text-gray-400">
                      {project.current_step}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <Link
                        to={`/projects/${project.id}`}
                        className="rounded bg-gray-700 px-3 py-1 text-xs text-white transition hover:bg-gray-600"
                      >
                        Open
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Create Project Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
          <div className="w-full max-w-lg rounded-xl bg-gray-800 p-6 shadow-xl">
            <h3 className="mb-4 text-lg font-bold text-white">
              New Project
            </h3>

            {createError && (
              <div className="mb-3 rounded-lg bg-red-900/50 px-3 py-2 text-sm text-red-300">
                {createError}
              </div>
            )}

            <form onSubmit={handleCreateProject} className="space-y-4">
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-300">
                  Name <span className="text-red-400">*</span>
                </label>
                <input
                  type="text"
                  value={newProject.name}
                  onChange={(e) =>
                    setNewProject((p) => ({ ...p, name: e.target.value }))
                  }
                  placeholder="My Project"
                  className="w-full rounded-lg border border-gray-600 bg-gray-900 px-4 py-2 text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-300">
                  Description
                </label>
                <textarea
                  value={newProject.description}
                  onChange={(e) =>
                    setNewProject((p) => ({
                      ...p,
                      description: e.target.value,
                    }))
                  }
                  rows={3}
                  placeholder="What this project does..."
                  className="w-full rounded-lg border border-gray-600 bg-gray-900 px-4 py-2 text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-300">
                  Architecture{' '}
                  <span className="text-gray-500">(optional)</span>
                </label>
                <textarea
                  value={newProject.architecture}
                  onChange={(e) =>
                    setNewProject((p) => ({
                      ...p,
                      architecture: e.target.value,
                    }))
                  }
                  rows={3}
                  placeholder="Tech stack, structure notes..."
                  className="w-full rounded-lg border border-gray-600 bg-gray-900 px-4 py-2 text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              </div>
              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => {
                    setShowModal(false);
                    setCreateError('');
                  }}
                  className="rounded-lg border border-gray-600 px-4 py-2 text-sm text-gray-300 transition hover:bg-gray-700"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createProject.isPending}
                  className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-blue-500 disabled:opacity-50"
                >
                  {createProject.isPending ? 'Creating...' : 'Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
}

const agentTypeRoutes: Record<string, (id: number) => string> = {
  research: (id) => `/research/${id}`,
  learning: (id) => `/learning/${id}`,
  social_media: (id) => `/social/${id}`,
};

const agentTypeLabels: Record<string, string> = {
  research: 'Research',
  learning: 'Learning',
  social_media: 'Social Media',
};

export default function AgentDetail() {
  const { id } = useParams<{ id: string }>();
  const agentId = Number(id);
  const { data: agent, isLoading, isError } = useAgent(agentId);

  if (isLoading) {
    return (
      <div className="p-6">
        <div className="h-8 w-48 animate-pulse rounded bg-gray-800" />
        <div className="mt-4 h-4 w-32 animate-pulse rounded bg-gray-800" />
      </div>
    );
  }

  if (isError || !agent) {
    return (
      <div className="p-6">
        <p className="text-red-400">Agent not found.</p>
      </div>
    );
  }

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white">{agent.name}</h1>
        <p className="mt-1 text-sm text-gray-400">
          {agent.type} &middot; {agent.model}
        </p>
      </div>

      {/* Render based on agent type */}
      {agent.type === 'coding' ? (
        <CodingAgentView agentId={agentId} />
      ) : agentTypeRoutes[agent.type] ? (
        <div className="rounded-lg bg-gray-800 p-8 text-center">
          <p className="mb-4 text-gray-400">
            This is a {agentTypeLabels[agent.type]} agent.
          </p>
          <Link
            to={agentTypeRoutes[agent.type](agentId)}
            className="inline-block rounded-lg bg-blue-600 px-5 py-2 text-white transition hover:bg-blue-500"
          >
            Go to {agentTypeLabels[agent.type]}
          </Link>
        </div>
      ) : (
        <div className="rounded-lg bg-gray-800 p-8 text-center">
          <p className="text-gray-400">
            Custom agent. Configuration was set during creation.
          </p>
        </div>
      )}
    </div>
  );
}
