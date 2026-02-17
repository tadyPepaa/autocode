import { useState, useRef, useEffect } from 'react';
import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useResearchMessages, useResearchSession } from '../api/research';
import MarkdownCanvas from './MarkdownCanvas';

interface ChatInterfaceProps {
  sessionId: number;
  onSendMessage: (content: string) => Promise<void>;
  isSending: boolean;
}

export default function ChatInterface({ sessionId, onSendMessage, isSending }: ChatInterfaceProps) {
  const { data: messages = [] } = useResearchMessages(sessionId);
  const { data: session } = useResearchSession(sessionId);
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const isThinking = session?.status === 'thinking';

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 160) + 'px';
    }
  }, [input]);

  async function handleSend() {
    const content = input.trim();
    if (!content || isSending || isThinking) return;
    setInput('');
    await onSendMessage(content);
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  return (
    <div className="flex h-[calc(100vh-12rem)] gap-4">
      {/* Chat messages - left side */}
      <div className="flex w-[60%] flex-col rounded-lg border border-gray-700 bg-gray-800">
        {/* Message list */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {messages.length === 0 && !isThinking && (
            <div className="flex h-full items-center justify-center">
              <div className="text-center">
                <p className="text-gray-400">Send a message to start researching.</p>
                <p className="mt-1 text-xs text-gray-600">
                  Claude will research the topic and create markdown documents.
                </p>
              </div>
            </div>
          )}
          {messages.map(msg => (
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
                {msg.role === 'assistant' ? (
                  <div className="prose prose-invert prose-sm max-w-none">
                    <Markdown remarkPlugins={[remarkGfm]}>{msg.content}</Markdown>
                  </div>
                ) : (
                  <p className="whitespace-pre-wrap">{msg.content}</p>
                )}
                <p className={`mt-1 text-xs ${msg.role === 'user' ? 'text-blue-300' : 'text-gray-500'}`}>
                  {new Date(msg.created_at).toLocaleTimeString()}
                </p>
              </div>
            </div>
          ))}

          {/* Thinking indicator */}
          {isThinking && (
            <div className="flex justify-start">
              <div className="rounded-lg bg-gray-700 px-4 py-2 text-sm text-gray-400">
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
        <div className="border-t border-gray-700 p-3">
          <div className="flex items-end gap-2">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={isThinking ? 'Waiting for response...' : 'Type a message... (Shift+Enter for newline)'}
              disabled={isSending || isThinking}
              rows={1}
              className="flex-1 resize-none rounded-lg border border-gray-600 bg-gray-900 px-4 py-2 text-sm text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:opacity-50"
            />
            <button
              onClick={handleSend}
              disabled={isSending || isThinking || !input.trim()}
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-blue-500 disabled:opacity-50"
            >
              {isSending ? 'Sending...' : 'Send'}
            </button>
          </div>
        </div>
      </div>

      {/* Markdown Canvas - right side */}
      <div className="w-[40%] rounded-lg border border-gray-700 bg-gray-800">
        <MarkdownCanvas sessionId={sessionId} />
      </div>
    </div>
  );
}
