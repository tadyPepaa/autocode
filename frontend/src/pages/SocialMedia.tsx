import { useState, useRef, useEffect, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { useSocialStories, useSocialAiChat, type Story } from '../api/social';
import Feed from '../components/social/Feed';
import PostComposer from '../components/social/PostComposer';
import Inbox from '../components/social/Inbox';

type Tab = 'feed' | 'stories' | 'new-post' | 'inbox' | 'ai';

interface ChatMessage {
  id: number;
  role: 'user' | 'assistant';
  content: string;
}

function StoriesView() {
  const { data: stories, isLoading, isError } = useSocialStories();

  if (isLoading) {
    return (
      <div className="flex gap-4 overflow-x-auto pb-2">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="h-48 w-32 shrink-0 animate-pulse rounded-xl bg-gray-800" />
        ))}
      </div>
    );
  }

  if (isError) {
    return (
      <div className="rounded-lg bg-gray-800 p-8 text-center">
        <p className="text-red-400">Failed to load stories.</p>
      </div>
    );
  }

  if (!stories || stories.length === 0) {
    return (
      <div className="rounded-lg bg-gray-800 p-8 text-center">
        <p className="text-gray-400">No stories available. Stories are Instagram-only.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-gray-400">Instagram Stories</p>
      <div className="flex gap-4 overflow-x-auto pb-2">
        {stories.map((story: Story) => (
          <div
            key={story.id}
            className="relative h-48 w-32 shrink-0 overflow-hidden rounded-xl border border-gray-700 bg-gray-800"
          >
            {story.media_url && (
              <img
                src={story.media_url}
                alt="Story"
                className="h-full w-full object-cover"
                onError={(e) => {
                  (e.target as HTMLImageElement).style.display = 'none';
                }}
              />
            )}
            <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/70 to-transparent px-2 py-2">
              <span className="text-xs text-gray-300">
                {new Date(story.timestamp).toLocaleString()}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function AiAssistant() {
  const aiChat = useSocialAiChat();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const nextIdRef = useRef(1);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  async function handleSend() {
    const content = input.trim();
    if (!content || aiChat.isPending) return;

    const userMsg: ChatMessage = {
      id: nextIdRef.current++,
      role: 'user',
      content,
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');

    try {
      const response = await aiChat.mutateAsync(content);
      const assistantMsg: ChatMessage = {
        id: nextIdRef.current++,
        role: 'assistant',
        content: response,
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch {
      const errorMsg: ChatMessage = {
        id: nextIdRef.current++,
        role: 'assistant',
        content: 'Failed to get response. Please try again.',
      };
      setMessages((prev) => [...prev, errorMsg]);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  return (
    <div className="mx-auto flex max-w-3xl flex-col" style={{ height: 'calc(100vh - 16rem)' }}>
      <div className="mb-3 text-sm text-gray-400">
        Ask the AI assistant about your social media strategy, content ideas, or analytics.
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto rounded-lg border border-gray-700 bg-gray-800 p-4">
        {messages.length === 0 && (
          <p className="mt-8 text-center text-gray-500">
            Start a conversation with your social media AI assistant.
          </p>
        )}
        <div className="space-y-3">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[80%] rounded-lg px-4 py-2 text-sm ${
                  msg.role === 'user'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-700 text-gray-200'
                }`}
              >
                <p className="whitespace-pre-wrap">{msg.content}</p>
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input */}
      <div className="mt-3 flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type a message..."
          disabled={aiChat.isPending}
          className="flex-1 rounded-lg border border-gray-600 bg-gray-800 px-4 py-2 text-sm text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:opacity-50"
        />
        <button
          onClick={handleSend}
          disabled={aiChat.isPending || !input.trim()}
          className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-blue-500 disabled:opacity-50"
        >
          {aiChat.isPending ? 'Sending...' : 'Send'}
        </button>
      </div>
    </div>
  );
}

export default function SocialMedia() {
  const { agentId } = useParams<{ agentId: string }>();
  const [tab, setTab] = useState<Tab>('feed');

  const tabs: { key: Tab; label: string }[] = [
    { key: 'feed', label: 'Feed' },
    { key: 'stories', label: 'Stories' },
    { key: 'new-post', label: 'New Post' },
    { key: 'inbox', label: 'Inbox' },
    { key: 'ai', label: 'AI Assistant' },
  ];

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white">Social Media Manager</h1>
        {agentId && (
          <p className="mt-1 text-sm text-gray-400">Agent #{agentId}</p>
        )}
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
      {tab === 'feed' && <Feed />}
      {tab === 'stories' && <StoriesView />}
      {tab === 'new-post' && <PostComposer />}
      {tab === 'inbox' && <Inbox />}
      {tab === 'ai' && <AiAssistant />}
    </div>
  );
}
