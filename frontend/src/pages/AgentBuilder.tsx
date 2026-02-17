import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useCreateAgent } from '../api/agents';
import api from '../api/client';

interface Template {
  type: string;
  model: string;
  identity: string;
  tools: string;
  global_rules: string;
}

interface FormData {
  name: string;
  type: string;
  model: string;
  identity: string;
  tools: string;
  mcp_servers: string;
  global_rules: string;
}

const templateMeta: Record<string, { icon: string; label: string }> = {
  coding: { icon: '\u{1F4BB}', label: 'Coding Agent' },
  research: { icon: '\u{1F52C}', label: 'Research Agent' },
  learning: { icon: '\u{1F393}', label: 'Learning Agent' },
  social_media: { icon: '\u{1F4F1}', label: 'Social Media' },
};

const modelSuggestions = [
  'openai/gpt-5.3-codex',
  'anthropic/claude-opus-4-6',
  'anthropic/claude-sonnet-4-5',
];

const emptyForm: FormData = {
  name: '',
  type: 'custom',
  model: '',
  identity: '',
  tools: '[]',
  mcp_servers: '[]',
  global_rules: '',
};

export default function AgentBuilder() {
  const navigate = useNavigate();
  const createAgent = useCreateAgent();
  const [selectedTemplate, setSelectedTemplate] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<FormData>(emptyForm);
  const [error, setError] = useState('');

  const { data: templates, isLoading } = useQuery<Record<string, Template>>({
    queryKey: ['agent-templates'],
    queryFn: () => api.get('/agents/templates').then((r) => r.data),
  });

  function selectTemplate(key: string, tmpl: Template) {
    setSelectedTemplate(key);
    setForm({
      name: '',
      type: tmpl.type,
      model: tmpl.model,
      identity: tmpl.identity,
      tools: tmpl.tools,
      mcp_servers: '[]',
      global_rules: tmpl.global_rules,
    });
    setShowForm(true);
    setError('');
  }

  function selectCustom() {
    setSelectedTemplate(null);
    setForm(emptyForm);
    setShowForm(true);
    setError('');
  }

  function cancelForm() {
    setShowForm(false);
    setSelectedTemplate(null);
    setForm(emptyForm);
    setError('');
  }

  function updateField(field: keyof FormData, value: string) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');

    if (!form.name.trim()) {
      setError('Name is required.');
      return;
    }
    if (!form.model.trim()) {
      setError('Model is required.');
      return;
    }

    try {
      const payload: Record<string, string> = {
        name: form.name.trim(),
        type: form.type || 'custom',
        model: form.model.trim(),
        identity: form.identity,
        tools: form.tools,
        mcp_servers: form.mcp_servers,
        global_rules: form.global_rules,
      };

      const created = await createAgent.mutateAsync(payload);
      navigate(`/agents/${created.id}`);
    } catch (err: unknown) {
      const msg =
        err instanceof Error
          ? err.message
          : 'Failed to create agent.';
      setError(msg);
    }
  }

  // Template selection view
  if (!showForm) {
    return (
      <div className="p-6">
        <h1 className="mb-6 text-2xl font-bold text-white">Create New Agent</h1>

        {/* Template grid */}
        <h2 className="mb-4 text-lg font-semibold text-gray-300">
          Choose a template
        </h2>

        {isLoading && (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <div
                key={i}
                className="h-44 animate-pulse rounded-lg bg-gray-800"
              />
            ))}
          </div>
        )}

        {templates && (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {Object.entries(templates).map(([key, tmpl]) => {
              const meta = templateMeta[key] ?? {
                icon: '\u2699\uFE0F',
                label: key,
              };
              return (
                <button
                  key={key}
                  onClick={() => selectTemplate(key, tmpl)}
                  className="flex flex-col items-start gap-3 rounded-lg bg-gray-800 p-6 text-left transition hover:bg-gray-700 hover:ring-2 hover:ring-blue-500"
                >
                  <span className="text-4xl">{meta.icon}</span>
                  <span className="text-lg font-semibold text-white">
                    {meta.label}
                  </span>
                  <span className="text-sm text-gray-400">{tmpl.model}</span>
                  <span className="mt-1 line-clamp-2 text-xs text-gray-500">
                    {tmpl.identity}
                  </span>
                </button>
              );
            })}
          </div>
        )}

        {/* Divider */}
        <div className="my-8 flex items-center gap-4">
          <div className="h-px flex-1 bg-gray-700" />
          <span className="text-sm text-gray-500">or</span>
          <div className="h-px flex-1 bg-gray-700" />
        </div>

        {/* Custom agent button */}
        <div className="text-center">
          <button
            onClick={selectCustom}
            className="rounded-lg border border-gray-600 bg-gray-800 px-6 py-3 text-white transition hover:bg-gray-700 hover:ring-2 hover:ring-blue-500"
          >
            Create Custom Agent
          </button>
        </div>
      </div>
    );
  }

  // Form view
  return (
    <div className="p-6">
      <h1 className="mb-6 text-2xl font-bold text-white">
        {selectedTemplate
          ? `New ${templateMeta[selectedTemplate]?.label ?? selectedTemplate}`
          : 'New Custom Agent'}
      </h1>

      {error && (
        <div className="mb-4 rounded-lg bg-red-900/50 px-4 py-3 text-red-300">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="max-w-2xl space-y-5">
        {/* Name */}
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-300">
            Name <span className="text-red-400">*</span>
          </label>
          <input
            type="text"
            value={form.name}
            onChange={(e) => updateField('name', e.target.value)}
            placeholder="My Agent"
            className="w-full rounded-lg border border-gray-600 bg-gray-800 px-4 py-2 text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>

        {/* Model */}
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-300">
            Model <span className="text-red-400">*</span>
          </label>
          <input
            type="text"
            list="model-suggestions"
            value={form.model}
            onChange={(e) => updateField('model', e.target.value)}
            placeholder="anthropic/claude-opus-4-6"
            className="w-full rounded-lg border border-gray-600 bg-gray-800 px-4 py-2 text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
          <datalist id="model-suggestions">
            {modelSuggestions.map((m) => (
              <option key={m} value={m} />
            ))}
          </datalist>
        </div>

        {/* Identity */}
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-300">
            Identity / Behavior Rules
          </label>
          <textarea
            value={form.identity}
            onChange={(e) => updateField('identity', e.target.value)}
            rows={6}
            placeholder="Describe the agent's personality, role, and behavior rules..."
            className="w-full rounded-lg border border-gray-600 bg-gray-800 px-4 py-2 text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>

        {/* Global Rules */}
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-300">
            Global Rules
          </label>
          <textarea
            value={form.global_rules}
            onChange={(e) => updateField('global_rules', e.target.value)}
            rows={4}
            placeholder="Rules the agent must always follow..."
            className="w-full rounded-lg border border-gray-600 bg-gray-800 px-4 py-2 text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>

        {/* Tools */}
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-300">
            Tools
          </label>
          <textarea
            value={form.tools}
            onChange={(e) => updateField('tools', e.target.value)}
            rows={3}
            placeholder='["tmux", "exec", "read_file", "write_file"]'
            className="w-full rounded-lg border border-gray-600 bg-gray-800 px-4 py-2 font-mono text-sm text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
          <p className="mt-1 text-xs text-gray-500">JSON array of tool names</p>
        </div>

        {/* MCP Servers */}
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-300">
            MCP Servers{' '}
            <span className="text-gray-500">(optional)</span>
          </label>
          <textarea
            value={form.mcp_servers}
            onChange={(e) => updateField('mcp_servers', e.target.value)}
            rows={3}
            placeholder="[]"
            className="w-full rounded-lg border border-gray-600 bg-gray-800 px-4 py-2 font-mono text-sm text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
          <p className="mt-1 text-xs text-gray-500">
            JSON array of MCP server configurations
          </p>
        </div>

        {/* Buttons */}
        <div className="flex gap-3 pt-2">
          <button
            type="button"
            onClick={cancelForm}
            className="rounded-lg border border-gray-600 px-5 py-2 text-gray-300 transition hover:bg-gray-700"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={createAgent.isPending}
            className="rounded-lg bg-blue-600 px-5 py-2 font-medium text-white transition hover:bg-blue-500 disabled:opacity-50"
          >
            {createAgent.isPending ? 'Creating...' : 'Create Agent'}
          </button>
        </div>
      </form>
    </div>
  );
}
