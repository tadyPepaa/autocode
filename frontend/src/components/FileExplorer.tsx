import { useState, useEffect, useMemo } from 'react';
import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import * as XLSX from 'xlsx';
import { useResearchFiles, useResearchFileContent, type ResearchFile } from '../api/research';
import { getRawFileUrl } from '../api/research';

interface FileExplorerProps {
  sessionId: number;
}

const CODE_EXTENSIONS = new Set([
  '.py', '.js', '.ts', '.tsx', '.jsx', '.json', '.css', '.html', '.yml', '.yaml', '.xml', '.toml',
  '.sh', '.bash', '.sql', '.rs', '.go', '.java', '.c', '.cpp', '.h', '.rb', '.php',
]);

const IMAGE_EXTENSIONS = new Set(['.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp']);
const PLAIN_EXTENSIONS = new Set(['.txt', '.csv', '.log']);
const EXCEL_EXTENSIONS = new Set(['.xlsx', '.xls']);
const PDF_EXTENSIONS = new Set(['.pdf']);
const MARKDOWN_EXTENSIONS = new Set(['.md', '.mdx']);

function getExtension(filename: string): string {
  const idx = filename.lastIndexOf('.');
  return idx >= 0 ? filename.slice(idx).toLowerCase() : '';
}

type FileType = 'markdown' | 'code' | 'plain' | 'image' | 'excel' | 'pdf' | 'other';

function getFileType(filename: string): FileType {
  const ext = getExtension(filename);
  if (MARKDOWN_EXTENSIONS.has(ext)) return 'markdown';
  if (CODE_EXTENSIONS.has(ext)) return 'code';
  if (PLAIN_EXTENSIONS.has(ext)) return 'plain';
  if (IMAGE_EXTENSIONS.has(ext)) return 'image';
  if (EXCEL_EXTENSIONS.has(ext)) return 'excel';
  if (PDF_EXTENSIONS.has(ext)) return 'pdf';
  return 'other';
}

const FILE_ICONS: Record<FileType, string> = {
  markdown: 'MD',
  code: '</>',
  plain: 'TXT',
  image: 'IMG',
  excel: 'XLS',
  pdf: 'PDF',
  other: '...',
};

const FILE_ICON_COLORS: Record<FileType, string> = {
  markdown: 'text-blue-400',
  code: 'text-green-400',
  plain: 'text-gray-400',
  image: 'text-purple-400',
  excel: 'text-emerald-400',
  pdf: 'text-red-400',
  other: 'text-gray-500',
};

function FileIcon({ filename }: { filename: string }) {
  const type = getFileType(filename);
  return (
    <span className={`inline-block w-6 text-center text-[0.6rem] font-bold ${FILE_ICON_COLORS[type]}`}>
      {FILE_ICONS[type]}
    </span>
  );
}

function getLanguage(filename: string): string {
  const ext = getExtension(filename);
  const map: Record<string, string> = {
    '.py': 'python', '.js': 'javascript', '.ts': 'typescript', '.tsx': 'tsx', '.jsx': 'jsx',
    '.json': 'json', '.css': 'css', '.html': 'html', '.yml': 'yaml', '.yaml': 'yaml',
    '.xml': 'xml', '.toml': 'toml', '.sh': 'bash', '.bash': 'bash', '.sql': 'sql',
    '.rs': 'rust', '.go': 'go', '.java': 'java', '.c': 'c', '.cpp': 'cpp', '.h': 'c',
    '.rb': 'ruby', '.php': 'php',
  };
  return map[ext] || 'text';
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes}B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)}MB`;
}

function ExcelPreview({ content }: { content: string }) {
  const tables = useMemo(() => {
    try {
      // content is base64 for binary files
      const wb = XLSX.read(content, { type: 'base64' });
      return wb.SheetNames.map(name => {
        const sheet = wb.Sheets[name];
        const html = XLSX.utils.sheet_to_html(sheet, { editable: false });
        return { name, html };
      });
    } catch {
      return null;
    }
  }, [content]);

  if (!tables) return <p className="text-gray-400">Failed to parse Excel file.</p>;

  return (
    <div className="space-y-4">
      {tables.map(t => (
        <div key={t.name}>
          {tables.length > 1 && (
            <h3 className="mb-2 text-sm font-medium text-gray-300">{t.name}</h3>
          )}
          <div
            className="overflow-auto rounded border border-gray-700 text-sm [&_table]:w-full [&_table]:border-collapse [&_td]:border [&_td]:border-gray-700 [&_td]:px-2 [&_td]:py-1 [&_td]:text-gray-300 [&_th]:border [&_th]:border-gray-700 [&_th]:bg-gray-700 [&_th]:px-2 [&_th]:py-1 [&_th]:text-gray-200"
            dangerouslySetInnerHTML={{ __html: t.html }}
          />
        </div>
      ))}
    </div>
  );
}

// Check if file type needs raw binary (not text content)
function needsRawContent(filename: string): boolean {
  const type = getFileType(filename);
  return type === 'image' || type === 'pdf' || type === 'excel';
}

export default function FileExplorer({ sessionId }: FileExplorerProps) {
  const { data: files } = useResearchFiles(sessionId);
  const [selectedPath, setSelectedPath] = useState<string | null>(null);

  const selectedFile = files?.find(f => f.path === selectedPath);
  const fileType = selectedFile ? getFileType(selectedFile.name) : null;
  const isTextFile = selectedFile ? !needsRawContent(selectedFile.name) : false;

  const { data: fileContent } = useResearchFileContent(
    sessionId,
    isTextFile ? selectedPath : null,
  );

  // For binary files, construct raw URL
  const rawUrl = selectedFile && needsRawContent(selectedFile.name)
    ? getRawFileUrl(sessionId, selectedFile.path)
    : null;

  // Auto-select the most recently modified file
  useEffect(() => {
    if (files && files.length > 0 && !selectedPath) {
      setSelectedPath(files[0].path);
    }
  }, [files, selectedPath]);

  // Reset selection if file no longer exists
  useEffect(() => {
    if (selectedPath && files && !files.find(f => f.path === selectedPath)) {
      setSelectedPath(files.length > 0 ? files[0].path : null);
    }
  }, [files, selectedPath]);

  if (!files || files.length === 0) {
    return (
      <div className="flex h-full items-center justify-center text-gray-500">
        <div className="text-center">
          <p className="text-sm">No files yet.</p>
          <p className="mt-1 text-xs text-gray-600">
            Files will appear here as the research progresses.
          </p>
        </div>
      </div>
    );
  }

  function handleDownload() {
    if (!selectedFile) return;
    const url = getRawFileUrl(sessionId, selectedFile.path);
    const a = document.createElement('a');
    a.href = url;
    a.download = selectedFile.name;
    a.click();
  }

  return (
    <div className="flex h-full flex-col">
      {/* File list */}
      <div className="border-b border-gray-700">
        <div className="flex items-center justify-between px-3 py-2">
          <span className="text-xs font-medium text-gray-400">Files</span>
          <span className="text-xs text-gray-600">{files.length}</span>
        </div>
        <div className="max-h-40 overflow-y-auto">
          {files.map((f: ResearchFile) => (
            <button
              key={f.path}
              onClick={() => setSelectedPath(f.path)}
              className={`flex w-full items-center justify-between px-3 py-1.5 text-xs transition ${
                selectedPath === f.path
                  ? 'bg-blue-600/20 text-blue-300'
                  : 'text-gray-400 hover:bg-gray-700/50 hover:text-gray-200'
              }`}
            >
              <span className="flex items-center gap-1.5 truncate">
                <FileIcon filename={f.name} />
                <span className="truncate">{f.path}</span>
              </span>
              <span className="ml-2 shrink-0 text-gray-600">{formatSize(f.size)}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Preview header */}
      {selectedFile && (
        <div className="flex items-center justify-between border-b border-gray-700 px-3 py-2">
          <span className="truncate text-sm text-gray-300">{selectedFile.name}</span>
          <button
            onClick={handleDownload}
            className="ml-2 shrink-0 rounded p-1 text-gray-400 transition hover:bg-gray-700 hover:text-white"
            title="Download file"
          >
            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5 5 5-5M12 15V3" />
            </svg>
          </button>
        </div>
      )}

      {/* Preview content */}
      <div className="flex-1 overflow-y-auto p-4">
        {selectedFile ? (
          <FilePreview
            fileType={fileType!}
            filename={selectedFile.name}
            textContent={fileContent?.content ?? null}
            rawUrl={rawUrl}
          />
        ) : (
          <div className="flex h-full items-center justify-center">
            <p className="text-sm text-gray-500">Select a file to preview</p>
          </div>
        )}
      </div>
    </div>
  );
}

function FilePreview({
  fileType,
  filename,
  textContent,
  rawUrl,
}: {
  fileType: FileType;
  filename: string;
  textContent: string | null;
  rawUrl: string | null;
}) {
  switch (fileType) {
    case 'markdown':
      if (textContent === null) return <Spinner />;
      return (
        <div className="prose prose-invert prose-sm max-w-none">
          <Markdown remarkPlugins={[remarkGfm]}>{textContent}</Markdown>
        </div>
      );

    case 'code':
      if (textContent === null) return <Spinner />;
      return (
        <SyntaxHighlighter
          language={getLanguage(filename)}
          style={oneDark}
          customStyle={{ margin: 0, borderRadius: '0.5rem', fontSize: '0.8rem' }}
          showLineNumbers
        >
          {textContent}
        </SyntaxHighlighter>
      );

    case 'plain':
      if (textContent === null) return <Spinner />;
      return (
        <pre className="whitespace-pre-wrap break-words font-mono text-sm text-gray-300">
          {textContent}
        </pre>
      );

    case 'image':
      if (!rawUrl) return <Spinner />;
      return (
        <div className="flex justify-center">
          <img src={rawUrl} alt={filename} className="max-h-[70vh] max-w-full rounded" />
        </div>
      );

    case 'excel':
      if (!rawUrl) return <Spinner />;
      return <ExcelPreviewFromUrl url={rawUrl} />;

    case 'pdf':
      if (!rawUrl) return <Spinner />;
      return (
        <iframe
          src={rawUrl}
          className="h-full w-full rounded border border-gray-700"
          title={filename}
        />
      );

    case 'other':
      return (
        <div className="flex flex-col items-center justify-center gap-3 py-12 text-gray-400">
          <span className="text-4xl text-gray-500">...</span>
          <p className="text-sm">{filename}</p>
          <p className="text-xs text-gray-600">Preview not available for this file type.</p>
        </div>
      );
  }
}

function ExcelPreviewFromUrl({ url }: { url: string }) {
  const [data, setData] = useState<string | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    fetch(url)
      .then(r => r.arrayBuffer())
      .then(buf => {
        if (cancelled) return;
        // Convert to base64
        const bytes = new Uint8Array(buf);
        let binary = '';
        for (let i = 0; i < bytes.length; i++) {
          binary += String.fromCharCode(bytes[i]);
        }
        setData(btoa(binary));
      })
      .catch(() => {
        if (!cancelled) setError(true);
      });
    return () => { cancelled = true; };
  }, [url]);

  if (error) return <p className="text-gray-400">Failed to load Excel file.</p>;
  if (!data) return <Spinner />;
  return <ExcelPreview content={data} />;
}

function Spinner() {
  return (
    <div className="flex h-full items-center justify-center">
      <div className="h-4 w-4 animate-spin rounded-full border-2 border-gray-600 border-t-blue-500" />
    </div>
  );
}
