import { useState } from 'react';
import { useSocialFeed, usePostComments, useReplyComment, type FeedItem } from '../../api/social';

function PlatformBadge({ platform }: { platform: string }) {
  const styles =
    platform === 'instagram'
      ? 'bg-gradient-to-r from-purple-500 to-pink-500'
      : 'bg-blue-600';
  return (
    <span className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium text-white ${styles}`}>
      {platform === 'instagram' ? 'IG' : 'FB'}
    </span>
  );
}

function PostComments({ postId, platform }: { postId: string; platform: string }) {
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
    return <div className="h-8 animate-pulse rounded bg-gray-700" />;
  }

  if (!comments || comments.length === 0) {
    return <p className="text-sm text-gray-500">No comments yet.</p>;
  }

  return (
    <div className="space-y-2">
      {comments.map((comment) => (
        <div key={comment.id} className="rounded-lg border border-gray-700 bg-gray-800/50 px-3 py-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-gray-400">
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
                placeholder="Reply..."
                className="flex-1 rounded border border-gray-600 bg-gray-900 px-3 py-1 text-sm text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none"
              />
              <button
                onClick={() => handleReply(comment.id)}
                disabled={replyComment.isPending}
                className="rounded bg-blue-600 px-3 py-1 text-xs text-white hover:bg-blue-500 disabled:opacity-50"
              >
                Send
              </button>
              <button
                onClick={() => { setReplyTo(null); setReplyText(''); }}
                className="rounded bg-gray-700 px-3 py-1 text-xs text-gray-300 hover:bg-gray-600"
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

function PostCard({ item }: { item: FeedItem }) {
  const [showComments, setShowComments] = useState(false);
  const caption = item.caption ?? item.message ?? '';

  return (
    <div className="rounded-lg border border-gray-700 bg-gray-800 overflow-hidden">
      {item.media_url && (
        <div className="aspect-square w-full bg-gray-900">
          <img
            src={item.media_url}
            alt={caption}
            className="h-full w-full object-cover"
            onError={(e) => {
              (e.target as HTMLImageElement).style.display = 'none';
            }}
          />
        </div>
      )}
      <div className="p-4">
        <div className="mb-2 flex items-center justify-between">
          <PlatformBadge platform={item.platform} />
          <span className="text-xs text-gray-500">
            {new Date(item.timestamp).toLocaleString()}
          </span>
        </div>
        {caption && (
          <p className="mb-3 text-sm text-gray-200 line-clamp-3">{caption}</p>
        )}
        <div className="flex items-center gap-4 text-xs text-gray-400">
          {item.like_count != null && (
            <span>{item.like_count} likes</span>
          )}
          {item.comments_count != null && (
            <button
              onClick={() => setShowComments(!showComments)}
              className="hover:text-white transition"
            >
              {item.comments_count} comments
            </button>
          )}
        </div>
        {showComments && (
          <div className="mt-3 border-t border-gray-700 pt-3">
            <PostComments postId={item.id} platform={item.platform} />
          </div>
        )}
      </div>
    </div>
  );
}

export default function Feed() {
  const { data: items, isLoading, isError } = useSocialFeed();

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="h-64 animate-pulse rounded-lg bg-gray-800" />
        ))}
      </div>
    );
  }

  if (isError) {
    return (
      <div className="rounded-lg bg-gray-800 p-8 text-center">
        <p className="text-red-400">Failed to load feed.</p>
      </div>
    );
  }

  if (!items || items.length === 0) {
    return (
      <div className="rounded-lg bg-gray-800 p-8 text-center">
        <p className="text-gray-400">No posts yet. Create your first post!</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
      {items.map((item) => (
        <PostCard key={item.id} item={item} />
      ))}
    </div>
  );
}
