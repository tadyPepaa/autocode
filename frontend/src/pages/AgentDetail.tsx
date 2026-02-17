import { useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useAgent, useUpdateAgent } from '../api/agents';
import { useProjects, useCreateProject, type Project } from '../api/projects';
import {
  useResearchSessions,
  useCreateResearch,
  useDeleteResearch,
  type ResearchSession,
} from '../api/research';
import {
  useSubjects,
  useCreateSubject,
  useDeleteSubject,
  useCourses,
  useCreateCourse,
  useDeleteCourse,
  type Subject,
  type Course,
} from '../api/learning';
import {
  useSocialAccounts,
  useConnectInstagram,
  useConnectFacebook,
  useDisconnectAccount,
} from '../api/social';

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

const researchStatusColors: Record<string, string> = {
  active: 'bg-green-600',
  stopped: 'bg-yellow-600',
};

function ResearchAgentView({ agentId }: { agentId: number }) {
  const { data: sessions, isLoading } = useResearchSessions(agentId);
  const createResearch = useCreateResearch(agentId);
  const deleteResearch = useDeleteResearch();
  const navigate = useNavigate();

  const [showModal, setShowModal] = useState(false);
  const [newName, setNewName] = useState('');
  const [createError, setCreateError] = useState('');

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setCreateError('');
    if (!newName.trim()) {
      setCreateError('Name is required.');
      return;
    }
    try {
      const created = (await createResearch.mutateAsync({
        name: newName.trim(),
      })) as ResearchSession;
      setShowModal(false);
      setNewName('');
      navigate(`/research/${created.id}`);
    } catch {
      setCreateError('Failed to create research session.');
    }
  }

  function handleDelete(id: number) {
    if (!confirm('Delete this research session?')) return;
    deleteResearch.mutate(id);
  }

  return (
    <section>
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-300">
          Research Sessions
        </h2>
        <button
          onClick={() => setShowModal(true)}
          className="rounded-lg bg-blue-600 px-4 py-1.5 text-sm font-medium text-white transition hover:bg-blue-500"
        >
          + New Research
        </button>
      </div>

      {isLoading && (
        <div className="space-y-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <div
              key={i}
              className="h-12 animate-pulse rounded-lg bg-gray-800"
            />
          ))}
        </div>
      )}

      {!isLoading && sessions && sessions.length === 0 && (
        <p className="text-gray-500">
          No research sessions yet. Create your first one.
        </p>
      )}

      {!isLoading && sessions && sessions.length > 0 && (
        <div className="overflow-hidden rounded-lg border border-gray-700">
          <table className="w-full text-left text-sm">
            <thead className="bg-gray-800 text-gray-400">
              <tr>
                <th className="px-4 py-3 font-medium">Name</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium">Created</th>
                <th className="px-4 py-3 font-medium" />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-700">
              {sessions.map((session) => (
                <tr key={session.id} className="hover:bg-gray-800/50">
                  <td className="px-4 py-3 text-white">{session.name}</td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium text-white ${researchStatusColors[session.status] ?? 'bg-gray-600'}`}
                    >
                      {session.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-400">
                    {new Date(session.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-3 text-right space-x-2">
                    <Link
                      to={`/research/${session.id}`}
                      className="rounded bg-gray-700 px-3 py-1 text-xs text-white transition hover:bg-gray-600"
                    >
                      Open
                    </Link>
                    <button
                      onClick={() => handleDelete(session.id)}
                      disabled={deleteResearch.isPending}
                      className="rounded bg-red-700 px-3 py-1 text-xs text-white transition hover:bg-red-600 disabled:opacity-50"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Create Research Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
          <div className="w-full max-w-lg rounded-xl bg-gray-800 p-6 shadow-xl">
            <h3 className="mb-4 text-lg font-bold text-white">
              New Research Session
            </h3>

            {createError && (
              <div className="mb-3 rounded-lg bg-red-900/50 px-3 py-2 text-sm text-red-300">
                {createError}
              </div>
            )}

            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-300">
                  Name <span className="text-red-400">*</span>
                </label>
                <input
                  type="text"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  placeholder="Research topic..."
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
                  disabled={createResearch.isPending}
                  className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-blue-500 disabled:opacity-50"
                >
                  {createResearch.isPending ? 'Creating...' : 'Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </section>
  );
}

function SubjectCourses({ subject }: { subject: Subject }) {
  const { data: courses, isLoading } = useCourses(subject.id);
  const createCourse = useCreateCourse(subject.id);
  const deleteCourse = useDeleteCourse();
  const navigate = useNavigate();

  const [showModal, setShowModal] = useState(false);
  const [newCourse, setNewCourse] = useState({ name: '', instructions: '' });
  const [createError, setCreateError] = useState('');

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setCreateError('');
    if (!newCourse.name.trim()) {
      setCreateError('Name is required.');
      return;
    }
    try {
      const created = (await createCourse.mutateAsync({
        name: newCourse.name.trim(),
        instructions: newCourse.instructions,
      })) as Course;
      setShowModal(false);
      setNewCourse({ name: '', instructions: '' });
      navigate(`/learning/course/${created.id}`);
    } catch {
      setCreateError('Failed to create course.');
    }
  }

  function handleDelete(id: number) {
    if (!confirm('Delete this course?')) return;
    deleteCourse.mutate(id);
  }

  return (
    <div className="mt-2 ml-4 space-y-2">
      {isLoading && (
        <div className="h-8 animate-pulse rounded bg-gray-700" />
      )}

      {!isLoading && courses && courses.length === 0 && (
        <p className="text-sm text-gray-500">No courses yet.</p>
      )}

      {!isLoading && courses && courses.map((course) => (
        <div
          key={course.id}
          className="flex items-center justify-between rounded-lg border border-gray-700 bg-gray-800/50 px-3 py-2"
        >
          <div className="min-w-0 flex-1">
            <Link
              to={`/learning/course/${course.id}`}
              className="text-sm font-medium text-blue-400 hover:text-blue-300"
            >
              {course.name}
            </Link>
            {course.instructions && (
              <p className="truncate text-xs text-gray-500">{course.instructions}</p>
            )}
          </div>
          <div className="ml-3 flex items-center gap-2">
            <Link
              to={`/learning/course/${course.id}`}
              className="rounded bg-gray-700 px-3 py-1 text-xs text-white transition hover:bg-gray-600"
            >
              Open
            </Link>
            <button
              onClick={() => handleDelete(course.id)}
              disabled={deleteCourse.isPending}
              className="rounded bg-red-700 px-3 py-1 text-xs text-white transition hover:bg-red-600 disabled:opacity-50"
            >
              Delete
            </button>
          </div>
        </div>
      ))}

      <button
        onClick={() => setShowModal(true)}
        className="rounded-lg border border-dashed border-gray-600 px-3 py-1.5 text-xs text-gray-400 transition hover:border-gray-500 hover:text-gray-300"
      >
        + New Course
      </button>

      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
          <div className="w-full max-w-lg rounded-xl bg-gray-800 p-6 shadow-xl">
            <h3 className="mb-4 text-lg font-bold text-white">
              New Course in &quot;{subject.name}&quot;
            </h3>

            {createError && (
              <div className="mb-3 rounded-lg bg-red-900/50 px-3 py-2 text-sm text-red-300">
                {createError}
              </div>
            )}

            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-300">
                  Name <span className="text-red-400">*</span>
                </label>
                <input
                  type="text"
                  value={newCourse.name}
                  onChange={(e) => setNewCourse((c) => ({ ...c, name: e.target.value }))}
                  placeholder="Course name..."
                  className="w-full rounded-lg border border-gray-600 bg-gray-900 px-4 py-2 text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-300">
                  Instructions <span className="text-gray-500">(optional)</span>
                </label>
                <textarea
                  value={newCourse.instructions}
                  onChange={(e) => setNewCourse((c) => ({ ...c, instructions: e.target.value }))}
                  rows={4}
                  placeholder="What should the AI focus on? Any specific learning goals..."
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
                  disabled={createCourse.isPending}
                  className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-blue-500 disabled:opacity-50"
                >
                  {createCourse.isPending ? 'Creating...' : 'Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

function LearningAgentView({ agentId }: { agentId: number }) {
  const { data: subjects, isLoading } = useSubjects(agentId);
  const createSubject = useCreateSubject(agentId);
  const deleteSubject = useDeleteSubject();

  const [showModal, setShowModal] = useState(false);
  const [newName, setNewName] = useState('');
  const [createError, setCreateError] = useState('');
  const [expanded, setExpanded] = useState<Record<number, boolean>>({});

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setCreateError('');
    if (!newName.trim()) {
      setCreateError('Name is required.');
      return;
    }
    try {
      const created = (await createSubject.mutateAsync({
        name: newName.trim(),
      })) as Subject;
      setShowModal(false);
      setNewName('');
      setExpanded((prev) => ({ ...prev, [created.id]: true }));
    } catch {
      setCreateError('Failed to create subject.');
    }
  }

  function handleDelete(id: number) {
    if (!confirm('Delete this subject and all its courses?')) return;
    deleteSubject.mutate(id);
  }

  function toggleExpand(id: number) {
    setExpanded((prev) => ({ ...prev, [id]: !prev[id] }));
  }

  return (
    <section>
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-300">Subjects</h2>
        <button
          onClick={() => setShowModal(true)}
          className="rounded-lg bg-blue-600 px-4 py-1.5 text-sm font-medium text-white transition hover:bg-blue-500"
        >
          + New Subject
        </button>
      </div>

      {isLoading && (
        <div className="space-y-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <div
              key={i}
              className="h-12 animate-pulse rounded-lg bg-gray-800"
            />
          ))}
        </div>
      )}

      {!isLoading && subjects && subjects.length === 0 && (
        <p className="text-gray-500">
          No subjects yet. Create your first subject to start learning.
        </p>
      )}

      {!isLoading && subjects && subjects.length > 0 && (
        <div className="space-y-3">
          {subjects.map((subject) => (
            <div
              key={subject.id}
              className="rounded-lg border border-gray-700 bg-gray-800"
            >
              <div className="flex items-center justify-between px-4 py-3">
                <button
                  onClick={() => toggleExpand(subject.id)}
                  className="flex items-center gap-2 text-left"
                >
                  <span className="text-gray-400 transition-transform" style={{
                    display: 'inline-block',
                    transform: expanded[subject.id] ? 'rotate(90deg)' : 'rotate(0deg)',
                  }}>
                    &#9654;
                  </span>
                  <span className="font-medium text-white">{subject.name}</span>
                </button>
                <button
                  onClick={() => handleDelete(subject.id)}
                  disabled={deleteSubject.isPending}
                  className="rounded bg-red-700 px-3 py-1 text-xs text-white transition hover:bg-red-600 disabled:opacity-50"
                >
                  Delete
                </button>
              </div>

              {expanded[subject.id] && (
                <div className="border-t border-gray-700 px-4 py-3">
                  <SubjectCourses subject={subject} />
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Create Subject Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
          <div className="w-full max-w-lg rounded-xl bg-gray-800 p-6 shadow-xl">
            <h3 className="mb-4 text-lg font-bold text-white">New Subject</h3>

            {createError && (
              <div className="mb-3 rounded-lg bg-red-900/50 px-3 py-2 text-sm text-red-300">
                {createError}
              </div>
            )}

            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-300">
                  Name <span className="text-red-400">*</span>
                </label>
                <input
                  type="text"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  placeholder="Subject name..."
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
                  disabled={createSubject.isPending}
                  className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-blue-500 disabled:opacity-50"
                >
                  {createSubject.isPending ? 'Creating...' : 'Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </section>
  );
}

function SocialMediaAgentView({ agentId }: { agentId: number }) {
  const { data: accounts, isLoading } = useSocialAccounts();
  const connectInstagram = useConnectInstagram();
  const connectFacebook = useConnectFacebook();
  const disconnectAccount = useDisconnectAccount();

  async function handleConnectInstagram() {
    try {
      const data = await connectInstagram.mutateAsync();
      window.open(data.auth_url, '_blank');
    } catch {
      // ignore
    }
  }

  async function handleConnectFacebook() {
    try {
      const data = await connectFacebook.mutateAsync();
      window.open(data.auth_url, '_blank');
    } catch {
      // ignore
    }
  }

  function handleDisconnect(id: number) {
    if (!confirm('Disconnect this account?')) return;
    disconnectAccount.mutate(id);
  }

  return (
    <section className="space-y-6">
      {/* Connected Accounts */}
      <div>
        <h2 className="mb-3 text-lg font-semibold text-gray-300">
          Connected Accounts
        </h2>

        {isLoading && (
          <div className="space-y-2">
            {Array.from({ length: 2 }).map((_, i) => (
              <div key={i} className="h-12 animate-pulse rounded-lg bg-gray-800" />
            ))}
          </div>
        )}

        {!isLoading && accounts && accounts.length === 0 && (
          <p className="text-gray-500">No accounts connected. Connect Instagram or Facebook below.</p>
        )}

        {!isLoading && accounts && accounts.length > 0 && (
          <div className="space-y-2">
            {accounts.map((account) => (
              <div
                key={account.id}
                className="flex items-center justify-between rounded-lg border border-gray-700 bg-gray-800 px-4 py-3"
              >
                <div className="flex items-center gap-3">
                  <span
                    className={`inline-flex h-8 w-8 items-center justify-center rounded-full text-sm font-bold text-white ${
                      account.platform === 'instagram'
                        ? 'bg-gradient-to-r from-purple-500 to-pink-500'
                        : 'bg-blue-600'
                    }`}
                  >
                    {account.platform === 'instagram' ? 'IG' : 'FB'}
                  </span>
                  <div>
                    <p className="text-sm font-medium text-white">{account.account_name}</p>
                    <p className="text-xs text-gray-500 capitalize">{account.platform}</p>
                  </div>
                </div>
                <button
                  onClick={() => handleDisconnect(account.id)}
                  disabled={disconnectAccount.isPending}
                  className="rounded bg-red-700 px-3 py-1 text-xs text-white transition hover:bg-red-600 disabled:opacity-50"
                >
                  Disconnect
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Connect Buttons */}
      <div>
        <h2 className="mb-3 text-lg font-semibold text-gray-300">
          Connect Platform
        </h2>
        <div className="flex gap-3">
          <button
            onClick={handleConnectInstagram}
            disabled={connectInstagram.isPending}
            className="rounded-lg bg-gradient-to-r from-purple-600 to-pink-600 px-5 py-2 text-sm font-medium text-white transition hover:from-purple-500 hover:to-pink-500 disabled:opacity-50"
          >
            {connectInstagram.isPending ? 'Connecting...' : 'Connect Instagram'}
          </button>
          <button
            onClick={handleConnectFacebook}
            disabled={connectFacebook.isPending}
            className="rounded-lg bg-blue-600 px-5 py-2 text-sm font-medium text-white transition hover:bg-blue-500 disabled:opacity-50"
          >
            {connectFacebook.isPending ? 'Connecting...' : 'Connect Facebook'}
          </button>
        </div>
        <p className="mt-2 text-xs text-gray-500">
          OAuth will open in a new tab. Refresh this page after connecting.
        </p>
      </div>

      {/* Link to Social Media Manager */}
      <div className="rounded-lg border border-gray-700 bg-gray-800 p-6 text-center">
        <p className="mb-3 text-gray-400">
          Manage posts, stories, and messages in the Social Media Manager.
        </p>
        <Link
          to={`/social/${agentId}`}
          className="inline-block rounded-lg bg-blue-600 px-5 py-2 text-white transition hover:bg-blue-500"
        >
          Open Social Media Manager
        </Link>
      </div>
    </section>
  );
}

const agentTypeRoutes: Record<string, (id: number) => string> = {};

const agentTypeLabels: Record<string, string> = {};

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
      ) : agent.type === 'research' ? (
        <ResearchAgentView agentId={agentId} />
      ) : agent.type === 'learning' ? (
        <LearningAgentView agentId={agentId} />
      ) : agent.type === 'social_media' ? (
        <SocialMediaAgentView agentId={agentId} />
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
