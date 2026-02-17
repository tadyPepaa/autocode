import { Link } from 'react-router-dom';
import { useAgents } from '../api/agents';
import AgentCard from '../components/AgentCard';

export default function Dashboard() {
  const { data: agents, isLoading, isError, error } = useAgents();

  return (
    <div className="p-6">
      <h1 className="mb-6 text-2xl font-bold text-white">Dashboard</h1>

      {isLoading && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <div
              key={i}
              className="h-32 animate-pulse rounded-lg bg-gray-800"
            />
          ))}
        </div>
      )}

      {isError && (
        <p className="text-red-400">
          Failed to load agents: {(error as Error).message}
        </p>
      )}

      {!isLoading && !isError && agents?.length === 0 && (
        <div className="rounded-lg bg-gray-800 p-8 text-center">
          <p className="mb-4 text-gray-400">
            No agents yet. Create your first agent.
          </p>
          <Link
            to="/agents/new"
            className="inline-block rounded-lg bg-blue-600 px-4 py-2 text-white transition hover:bg-blue-500"
          >
            Create Agent
          </Link>
        </div>
      )}

      {!isLoading && !isError && agents && agents.length > 0 && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {agents.map((agent) => (
            <AgentCard key={agent.id} agent={agent} />
          ))}
        </div>
      )}
    </div>
  );
}
