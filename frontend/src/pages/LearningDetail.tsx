import { useParams, Navigate } from 'react-router-dom';

export default function LearningDetail() {
  const { agentId } = useParams<{ agentId: string }>();

  if (agentId) {
    return <Navigate to={`/agents/${agentId}`} replace />;
  }

  return (
    <div className="p-6">
      <p className="text-gray-400">Redirecting...</p>
    </div>
  );
}
