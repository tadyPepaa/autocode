import { useState, useRef, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  useCourse,
  useSubject,
  useCourseMessages,
  useSendCourseMessage,
  type ChatMessage,
} from '../api/learning';

export default function CourseChat() {
  const { id } = useParams<{ id: string }>();
  const courseId = Number(id);
  const navigate = useNavigate();

  const { data: course, isLoading: courseLoading } = useCourse(courseId);
  const { data: subject } = useSubject(course?.subject_id ?? 0);
  const { data: serverMessages, isLoading: messagesLoading } = useCourseMessages(courseId);
  const sendMessage = useSendCourseMessage();

  const [localMessages, setLocalMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Sync server messages into local state
  useEffect(() => {
    if (serverMessages) {
      setLocalMessages(serverMessages);
    }
  }, [serverMessages]);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [localMessages]);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 160) + 'px';
    }
  }, [input]);

  async function handleSend() {
    const content = input.trim();
    if (!content || sending) return;

    const userMessage: ChatMessage = {
      id: Date.now(),
      role: 'user',
      content,
      created_at: new Date().toISOString(),
    };

    setLocalMessages((prev) => [...prev, userMessage]);
    setInput('');
    setSending(true);

    try {
      const response = await sendMessage.mutateAsync({ courseId, content });
      setLocalMessages((prev) => [...prev, response as ChatMessage]);
    } catch {
      setLocalMessages((prev) => [
        ...prev,
        {
          id: Date.now() + 1,
          role: 'assistant',
          content: 'Failed to get response. Please try again.',
          created_at: new Date().toISOString(),
        },
      ]);
    } finally {
      setSending(false);
      textareaRef.current?.focus();
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  if (courseLoading) {
    return (
      <div className="flex h-full flex-col p-6">
        <div className="h-6 w-48 animate-pulse rounded bg-gray-800" />
        <div className="mt-4 h-4 w-32 animate-pulse rounded bg-gray-800" />
      </div>
    );
  }

  if (!course) {
    return (
      <div className="p-6">
        <p className="text-red-400">Course not found.</p>
        <button
          onClick={() => navigate(-1)}
          className="mt-3 text-sm text-blue-400 hover:text-blue-300"
        >
          Go back
        </button>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="flex items-center gap-3 border-b border-gray-700 bg-gray-900 px-4 py-3">
        <button
          onClick={() => navigate(-1)}
          className="rounded-lg border border-gray-600 px-3 py-1.5 text-sm text-gray-300 transition hover:bg-gray-700"
        >
          Back
        </button>
        <div className="min-w-0">
          <div className="flex items-center gap-1.5 text-sm text-gray-400">
            {subject && (
              <>
                <Link
                  to={`/agents/${course.subject_id}`}
                  className="hover:text-gray-300"
                >
                  {subject.name}
                </Link>
                <span>/</span>
              </>
            )}
            <span className="truncate font-medium text-white">{course.name}</span>
          </div>
          {course.instructions && (
            <p className="truncate text-xs text-gray-500">{course.instructions}</p>
          )}
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4">
        {messagesLoading && (
          <div className="space-y-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <div
                key={i}
                className={`h-12 w-2/3 animate-pulse rounded-lg bg-gray-800 ${i % 2 === 0 ? '' : 'ml-auto'}`}
              />
            ))}
          </div>
        )}

        {!messagesLoading && localMessages.length === 0 && (
          <div className="flex h-full items-center justify-center">
            <div className="text-center">
              <p className="text-lg text-gray-400">Start a conversation</p>
              <p className="mt-1 text-sm text-gray-500">
                Ask a question to begin learning about this topic.
              </p>
            </div>
          </div>
        )}

        {localMessages.map((msg) => (
          <div
            key={msg.id}
            className={`mb-3 flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[75%] rounded-lg px-4 py-2.5 text-sm ${
                msg.role === 'user'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-800 text-gray-200'
              }`}
            >
              <div className="whitespace-pre-wrap break-words">{msg.content}</div>
              <div
                className={`mt-1 text-[10px] ${
                  msg.role === 'user' ? 'text-blue-300' : 'text-gray-500'
                }`}
              >
                {new Date(msg.created_at).toLocaleTimeString()}
              </div>
            </div>
          </div>
        ))}

        {sending && (
          <div className="mb-3 flex justify-start">
            <div className="rounded-lg bg-gray-800 px-4 py-2.5 text-sm text-gray-400">
              <span className="inline-flex gap-1">
                <span className="animate-bounce">.</span>
                <span className="animate-bounce" style={{ animationDelay: '0.1s' }}>.</span>
                <span className="animate-bounce" style={{ animationDelay: '0.2s' }}>.</span>
              </span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="border-t border-gray-700 bg-gray-900 px-4 py-3">
        <div className="flex items-end gap-3">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type a message... (Shift+Enter for newline)"
            rows={1}
            disabled={sending}
            className="flex-1 resize-none rounded-lg border border-gray-600 bg-gray-800 px-4 py-2.5 text-sm text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:opacity-50"
          />
          <button
            onClick={handleSend}
            disabled={sending || !input.trim()}
            className="rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-blue-500 disabled:opacity-50"
          >
            {sending ? 'Sending...' : 'Send'}
          </button>
        </div>
      </div>
    </div>
  );
}
