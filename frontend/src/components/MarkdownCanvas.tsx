import { useState, useEffect } from 'react';
import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useResearchFiles, useResearchFileContent, type ResearchFile } from '../api/research';

interface MarkdownCanvasProps {
  sessionId: number;
}

export default function MarkdownCanvas({ sessionId }: MarkdownCanvasProps) {
  const { data: files } = useResearchFiles(sessionId);
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const { data: fileContent } = useResearchFileContent(sessionId, selectedPath);

  // Auto-select the most recently modified file
  useEffect(() => {
    if (files && files.length > 0 && !selectedPath) {
      setSelectedPath(files[0].path);
    }
  }, [files, selectedPath]);

  if (!files || files.length === 0) {
    return (
      <div className="flex h-full items-center justify-center text-gray-500">
        <div className="text-center">
          <p className="text-sm">No markdown files yet.</p>
          <p className="mt-1 text-xs text-gray-600">
            Files will appear here as the research progresses.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      {/* File tabs */}
      {files.length > 1 && (
        <div className="flex gap-1 border-b border-gray-700 px-2 py-1 overflow-x-auto">
          {files.map((f: ResearchFile) => (
            <button
              key={f.path}
              onClick={() => setSelectedPath(f.path)}
              className={`whitespace-nowrap rounded px-2 py-1 text-xs transition ${
                selectedPath === f.path
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-400 hover:bg-gray-700 hover:text-gray-200'
              }`}
            >
              {f.name}
            </button>
          ))}
        </div>
      )}

      {/* Markdown content */}
      <div className="flex-1 overflow-y-auto p-4">
        {fileContent ? (
          <div className="prose prose-invert prose-sm max-w-none">
            <Markdown remarkPlugins={[remarkGfm]}>{fileContent.content}</Markdown>
          </div>
        ) : (
          <div className="flex h-full items-center justify-center">
            <div className="h-4 w-4 animate-spin rounded-full border-2 border-gray-600 border-t-blue-500" />
          </div>
        )}
      </div>
    </div>
  );
}
