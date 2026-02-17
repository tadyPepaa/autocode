import { useState } from 'react';
import {
  usePostComments,
  useReplyComment,
  useSocialDms,
  useReplyDm,
  useSocialFeed,
  type DmConversation,
} from '../../api/social';

function CommentsSection() {
  const { data: feedItems } = useSocialFeed();
  const [selectedPostId, setSelectedPostId] = useState<string | null>(null);
  const [selectedPlatform, setSelectedPlatform] = useState<string>('instagram');

  // Pick the first post with comments, or let user select
  const postsWithComments = feedItems?.filter((item) => (item.comments_count ?? 0) > 0) ?? [];

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-white">Comments</h3>

      {postsWithComments.length === 0 && !selectedPostId && (
        <p className="text-sm text-gray-500">No posts with comments found.</p>
      )}

      {postsWithComments.length > 0 && (
        <div className="space-y-2">
          <label className="block text-sm font-medium text-gray-300">Select post</label>
          <select
            value={selectedPostId ?? ''}
            onChange={(e) => {
              const post = postsWithComments.find((p) => p.id === e.target.value);
              setSelectedPostId(e.target.value || null);
              if (post) setSelectedPlatform(post.platform);
            }}
            className="w-full rounded-lg border border-gray-600 bg-gray-900 px-4 py-2 text-white focus:border-blue-500 focus:outline-none"
          >
            <option value="">Choose a post...</option>
            {postsWithComments.map((post) => (
              <option key={post.id} value={post.id}>
                [{post.platform.toUpperCase()}] {(post.caption ?? post.message ?? '').slice(0, 60)}...
              </option>
            ))}
          </select>
        </div>
      )}

      {selectedPostId && (
        <PostCommentsInbox postId={selectedPostId} platform={selectedPlatform} />
      )}
    </div>
  );
}

function PostCommentsInbox({ postId, platform }: { postId: string; platform: string }) {
  const { data: comments, isLoading } = usePostComments(postId, platform);
  const replyComment = useReplyComment();
  const [replyTo, setReplyTo] = useState<string | null>(null);
  const [replyText, setReplyText] = useState('');

  function handleReply(commentId: string) {
    if (!replyText.trim()) return;
    replyComment.mutate(
      { commentId, message: replyText.trim(), platform },
      {
        onSuccess: () => {
          setReplyText('');
          setReplyTo(null);
        },
      },
    );
  }

  if (isLoading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="h-16 animate-pulse rounded-lg bg-gray-700" />
        ))}
      </div>
    );
  }

  if (!comments || comments.length === 0) {
    return <p className="text-sm text-gray-500">No comments on this post.</p>;
  }

  return (
    <div className="space-y-2">
      {comments.map((comment) => (
        <div key={comment.id} className="rounded-lg border border-gray-700 bg-gray-800/50 px-4 py-3">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-gray-300">
              {comment.username ?? 'User'}
            </span>
            <span className="text-xs text-gray-500">
              {new Date(comment.timestamp).toLocaleString()}
            </span>
          </div>
          <p className="mt-1 text-sm text-gray-200">{comment.text ?? comment.message}</p>

          {replyTo === comment.id ? (
            <div className="mt-2 flex gap-2">
              <input
                type="text"
                value={replyText}
                onChange={(e) => setReplyText(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleReply(comment.id);
                }}
                placeholder="Write a reply..."
                className="flex-1 rounded border border-gray-600 bg-gray-900 px-3 py-1.5 text-sm text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none"
              />
              <button
                onClick={() => handleReply(comment.id)}
                disabled={replyComment.isPending}
                className="rounded bg-blue-600 px-3 py-1.5 text-xs text-white hover:bg-blue-500 disabled:opacity-50"
              >
                Send
              </button>
              <button
                onClick={() => { setReplyTo(null); setReplyText(''); }}
                className="rounded bg-gray-700 px-3 py-1.5 text-xs text-gray-300 hover:bg-gray-600"
              >
                Cancel
              </button>
            </div>
          ) : (
            <button
              onClick={() => setReplyTo(comment.id)}
              className="mt-1 text-xs text-blue-400 hover:text-blue-300"
            >
              Reply
            </button>
          )}
        </div>
      ))}
    </div>
  );
}

function DmThread({ conversation }: { conversation: DmConversation }) {
  const replyDm = useReplyDm();
  const [replyText, setReplyText] = useState('');
  const [expanded, setExpanded] = useState(false);

  function handleReply() {
    if (!replyText.trim()) return;
    replyDm.mutate(
      { threadId: conversation.id, message: replyText.trim() },
      { onSuccess: () => setReplyText('') },
    );
  }

  const lastMessage = conversation.messages[conversation.messages.length - 1];

  return (
    <div className="rounded-lg border border-gray-700 bg-gray-800/50">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center justify-between px-4 py-3 text-left"
      >
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-gray-300">
            {conversation.participants.join(', ')}
          </p>
          {lastMessage && (
            <p className="mt-0.5 truncate text-xs text-gray-500">
              {lastMessage.text}
            </p>
          )}
        </div>
        <span className="ml-2 text-gray-400 transition-transform" style={{
          display: 'inline-block',
          transform: expanded ? 'rotate(90deg)' : 'rotate(0deg)',
        }}>
          &#9654;
        </span>
      </button>

      {expanded && (
        <div className="border-t border-gray-700 px-4 py-3">
          <div className="max-h-64 space-y-2 overflow-y-auto">
            {conversation.messages.map((msg) => (
              <div key={msg.id} className="rounded bg-gray-900/50 px-3 py-2">
                {msg.from && (
                  <span className="text-xs font-medium text-gray-400">{msg.from}</span>
                )}
                <p className="text-sm text-gray-200">{msg.text}</p>
                <span className="text-xs text-gray-500">
                  {new Date(msg.timestamp).toLocaleString()}
                </span>
              </div>
            ))}
          </div>

          <div className="mt-3 flex gap-2">
            <input
              type="text"
              value={replyText}
              onChange={(e) => setReplyText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleReply();
              }}
              placeholder="Write a reply..."
              className="flex-1 rounded border border-gray-600 bg-gray-900 px-3 py-1.5 text-sm text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none"
            />
            <button
              onClick={handleReply}
              disabled={replyDm.isPending || !replyText.trim()}
              className="rounded bg-blue-600 px-3 py-1.5 text-xs text-white hover:bg-blue-500 disabled:opacity-50"
            >
              {replyDm.isPending ? 'Sending...' : 'Send'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function DmsSection() {
  const { data: conversations, isLoading } = useSocialDms();

  if (isLoading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="h-16 animate-pulse rounded-lg bg-gray-700" />
        ))}
      </div>
    );
  }

  if (!conversations || conversations.length === 0) {
    return <p className="text-sm text-gray-500">No conversations yet.</p>;
  }

  return (
    <div className="space-y-2">
      {conversations.map((conv) => (
        <DmThread key={conv.id} conversation={conv} />
      ))}
    </div>
  );
}

export default function Inbox() {
  const [section, setSection] = useState<'comments' | 'dms'>('comments');

  return (
    <div className="space-y-4">
      {/* Section toggle */}
      <div className="flex gap-1 rounded-lg bg-gray-800 p-1">
        <button
          onClick={() => setSection('comments')}
          className={`rounded-md px-4 py-2 text-sm font-medium transition ${
            section === 'comments'
              ? 'bg-gray-700 text-white'
              : 'text-gray-400 hover:text-white'
          }`}
        >
          Comments
        </button>
        <button
          onClick={() => setSection('dms')}
          className={`rounded-md px-4 py-2 text-sm font-medium transition ${
            section === 'dms'
              ? 'bg-gray-700 text-white'
              : 'text-gray-400 hover:text-white'
          }`}
        >
          Direct Messages
        </button>
      </div>

      {section === 'comments' ? <CommentsSection /> : <DmsSection />}
    </div>
  );
}
