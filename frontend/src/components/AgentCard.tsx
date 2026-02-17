import { useNavigate } from 'react-router-dom';
import type { Agent } from '../api/agents';

const typeIcons: Record<string, string> = {
  coding: '\u{1F4BB}',
  research: '\u{1F52C}',
  learning: '\u{1F393}',
  social_media: '\u{1F4F1}',
  custom: '\u{2699}\u{FE0F}',
};

export default function AgentCard({ agent }: { agent: Agent }) {
  const navigate = useNavigate();
  const icon = typeIcons[agent.type] ?? typeIcons.custom;

  return (
    <button
      onClick={() => navigate(`/agents/${agent.id}`)}
      className="flex flex-col items-start gap-2 rounded-lg bg-gray-800 p-5 text-left transition hover:bg-gray-700"
    >
      <span className="text-3xl">{icon}</span>
      <span className="text-lg font-semibold text-white">{agent.name}</span>
      <span className="text-sm text-gray-400">{agent.model}</span>
    </button>
  );
}
