import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { FileCode } from 'lucide-react'
import type { FilePreview as FilePreviewType } from '../../types'

interface FilePreviewProps {
  file: FilePreviewType | null
}

function getLanguageFromPath(path: string): string {
  const ext = path.split('.').pop()?.toLowerCase()
  const langMap: Record<string, string> = {
    py: 'python',
    js: 'javascript',
    ts: 'typescript',
    tsx: 'tsx',
    jsx: 'jsx',
    json: 'json',
    md: 'markdown',
    yaml: 'yaml',
    yml: 'yaml',
    sh: 'bash',
    css: 'css',
    html: 'html',
    sql: 'sql',
  }
  return langMap[ext || ''] || 'text'
}

export function FilePreview({ file }: FilePreviewProps) {
  if (!file) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-text-muted p-4">
        <FileCode size={48} className="mb-4 opacity-50" />
        <p className="text-center">No file selected</p>
        <p className="text-sm text-center mt-2">
          File previews will appear here when the agent reads or writes files
        </p>
      </div>
    )
  }

  const language = file.language || getLanguageFromPath(file.path)

  return (
    <div className="p-4">
      {/* File Path */}
      <div className="flex items-center gap-2 mb-3 text-sm">
        <FileCode size={16} className="text-text-muted" />
        <span className="text-text-muted font-mono truncate">{file.path}</span>
      </div>

      {/* Code */}
      <div className="rounded-lg overflow-hidden">
        <SyntaxHighlighter
          language={language}
          style={oneDark}
          customStyle={{
            margin: 0,
            fontSize: '0.75rem',
            maxHeight: 'calc(100vh - 200px)',
          }}
          showLineNumbers
        >
          {file.content}
        </SyntaxHighlighter>
      </div>
    </div>
  )
}
