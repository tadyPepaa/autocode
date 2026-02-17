import { useParams, useNavigate } from 'react-router-dom';
import { useResearchSession, useResearchAction, useSendMessage } from '../api/research';
import ChatInterface from '../components/ChatInterface';

const statusColors: Record<string, string> = {
  active: 'bg-green-600',
  stopped: 'bg-yellow-600',
};

export default function ResearchChat() {
  const { id } = useParams<{ id: string }>();
  const sessionId = Number(id);
  const navigate = useNavigate();
  const { data: session, isLoading, isError } = useResearchSession(sessionId);
  const researchAction = useResearchAction();
  const sendMessage = useSendMessage();

  async function handleSendMessage(content: string) {
    await sendMessage.mutateAsync({ sessionId, content });
  }

  function handleAction(action: 'resume' | 'stop') {
    researchAction.mutate({ id: sessionId, action });
  }

  if (isLoading) {
    return (
      <div className="p-6">
        <div className="h-8 w-64 animate-pulse rounded bg-gray-800" />
        <div className="mt-4 h-4 w-32 animate-pulse rounded bg-gray-800" />
      </div>
    );
  }

  if (isError || !session) {
    return (
      <div className="p-6">
        <p className="text-red-400">Research session not found.</p>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col p-6">
      {/* Header */}
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate(-1)}
            className="rounded-lg border border-gray-600 px-3 py-1.5 text-sm text-gray-300 transition hover:bg-gray-700"
          >
            Back
          </button>
          <div>
            <h1 className="text-xl font-bold text-white">{session.name}</h1>
            <div className="mt-0.5 flex items-center gap-2">
              <span
                className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium text-white ${statusColors[session.status] ?? 'bg-gray-600'}`}
              >
                {session.status}
              </span>
              <span className="text-xs text-gray-500">{session.slug}</span>
            </div>
          </div>
        </div>

        <div className="flex gap-2">
          {session.status === 'stopped' && (
            <button
              onClick={() => handleAction('resume')}
              disabled={researchAction.isPending}
              className="rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-green-500 disabled:opacity-50"
            >
              Resume
            </button>
          )}
          {session.status === 'active' && (
            <button
              onClick={() => handleAction('stop')}
              disabled={researchAction.isPending}
              className="rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-red-500 disabled:opacity-50"
            >
              Stop
            </button>
          )}
        </div>
      </div>

      {/* Chat Interface */}
      <ChatInterface
        sessionId={sessionId}
        onSendMessage={handleSendMessage}
        isSending={sendMessage.isPending}
      />
    </div>
  );
}
