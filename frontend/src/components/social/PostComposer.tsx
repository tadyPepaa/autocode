import { useState } from 'react';
import { usePublishPost } from '../../api/social';

type Platform = 'instagram' | 'facebook' | 'both';

export default function PostComposer() {
  const publishPost = usePublishPost();
  const [caption, setCaption] = useState('');
  const [imageUrl, setImageUrl] = useState('');
  const [platform, setPlatform] = useState<Platform>('both');
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState('');

  async function handlePublish(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setSuccess(false);

    if (!caption.trim()) {
      setError('Caption is required.');
      return;
    }

    try {
      await publishPost.mutateAsync({
        platform,
        caption: caption.trim(),
        image_url: imageUrl.trim() || undefined,
      });
      setSuccess(true);
      setCaption('');
      setImageUrl('');
      setTimeout(() => setSuccess(false), 3000);
    } catch {
      setError('Failed to publish post.');
    }
  }

  const platformOptions: { value: Platform; label: string; style: string; activeStyle: string }[] = [
    {
      value: 'instagram',
      label: 'Instagram',
      style: 'border-gray-600 text-gray-400 hover:border-purple-500 hover:text-purple-400',
      activeStyle: 'border-purple-500 bg-gradient-to-r from-purple-500/20 to-pink-500/20 text-purple-300',
    },
    {
      value: 'facebook',
      label: 'Facebook',
      style: 'border-gray-600 text-gray-400 hover:border-blue-500 hover:text-blue-400',
      activeStyle: 'border-blue-500 bg-blue-500/20 text-blue-300',
    },
    {
      value: 'both',
      label: 'Both',
      style: 'border-gray-600 text-gray-400 hover:border-green-500 hover:text-green-400',
      activeStyle: 'border-green-500 bg-green-500/20 text-green-300',
    },
  ];

  return (
    <div className="mx-auto max-w-2xl">
      <div className="rounded-lg border border-gray-700 bg-gray-800 p-6">
        <h3 className="mb-4 text-lg font-semibold text-white">New Post</h3>

        {error && (
          <div className="mb-4 rounded-lg bg-red-900/50 px-3 py-2 text-sm text-red-300">
            {error}
          </div>
        )}

        {success && (
          <div className="mb-4 rounded-lg bg-green-900/50 px-3 py-2 text-sm text-green-300">
            Post published successfully!
          </div>
        )}

        <form onSubmit={handlePublish} className="space-y-4">
          {/* Platform selection */}
          <div>
            <label className="mb-2 block text-sm font-medium text-gray-300">
              Platform
            </label>
            <div className="flex gap-2">
              {platformOptions.map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => setPlatform(opt.value)}
                  className={`rounded-lg border px-4 py-2 text-sm font-medium transition ${
                    platform === opt.value ? opt.activeStyle : opt.style
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {/* Image URL */}
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-300">
              Image URL <span className="text-gray-500">(optional)</span>
            </label>
            <input
              type="url"
              value={imageUrl}
              onChange={(e) => setImageUrl(e.target.value)}
              placeholder="https://example.com/image.jpg"
              className="w-full rounded-lg border border-gray-600 bg-gray-900 px-4 py-2 text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
            {imageUrl && (
              <div className="mt-2 overflow-hidden rounded-lg border border-gray-700">
                <img
                  src={imageUrl}
                  alt="Preview"
                  className="max-h-48 w-full object-cover"
                  onError={(e) => {
                    (e.target as HTMLImageElement).style.display = 'none';
                  }}
                />
              </div>
            )}
          </div>

          {/* Caption */}
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-300">
              Caption <span className="text-red-400">*</span>
            </label>
            <textarea
              value={caption}
              onChange={(e) => setCaption(e.target.value)}
              rows={5}
              placeholder="Write your caption..."
              className="w-full rounded-lg border border-gray-600 bg-gray-900 px-4 py-2 text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
            <p className="mt-1 text-xs text-gray-500">{caption.length} characters</p>
          </div>

          {/* Submit */}
          <button
            type="submit"
            disabled={publishPost.isPending || !caption.trim()}
            className="w-full rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-blue-500 disabled:opacity-50"
          >
            {publishPost.isPending ? 'Publishing...' : 'Publish Post'}
          </button>
        </form>
      </div>
    </div>
  );
}
