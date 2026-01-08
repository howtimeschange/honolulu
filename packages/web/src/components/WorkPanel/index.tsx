import { useState } from 'react'
import { FilePreview } from './FilePreview'
import { ToolHistory } from './ToolHistory'
import type { ToolCall, FilePreview as FilePreviewType } from '../../types'
import { X, FileCode, Wrench } from 'lucide-react'

interface WorkPanelProps {
  toolCalls: ToolCall[]
  filePreview: FilePreviewType | null
  onConfirm: (toolCallId: string, action: 'allow' | 'deny' | 'allow_all') => void
  onClose: () => void
}

type Tab = 'files' | 'tools'

export function WorkPanel({ toolCalls, filePreview, onConfirm, onClose }: WorkPanelProps) {
  const [activeTab, setActiveTab] = useState<Tab>('tools')

  const pendingConfirmations = toolCalls.filter(tc => tc.status === 'awaiting_confirmation')

  return (
    <aside className="w-96 border-l border-border flex flex-col bg-surface">
      {/* Header */}
      <div className="h-12 border-b border-border flex items-center justify-between px-4">
        <div className="flex gap-2">
          <button
            onClick={() => setActiveTab('files')}
            className={`flex items-center gap-1 px-3 py-1 rounded text-sm transition-colors ${
              activeTab === 'files'
                ? 'bg-surface-light text-text'
                : 'text-text-muted hover:text-text'
            }`}
          >
            <FileCode size={16} />
            <span>Files</span>
          </button>
          <button
            onClick={() => setActiveTab('tools')}
            className={`flex items-center gap-1 px-3 py-1 rounded text-sm transition-colors ${
              activeTab === 'tools'
                ? 'bg-surface-light text-text'
                : 'text-text-muted hover:text-text'
            }`}
          >
            <Wrench size={16} />
            <span>Tools</span>
            {pendingConfirmations.length > 0 && (
              <span className="ml-1 px-1.5 py-0.5 text-xs bg-warning text-surface rounded-full">
                {pendingConfirmations.length}
              </span>
            )}
          </button>
        </div>
        <button
          onClick={onClose}
          className="p-1 hover:bg-surface-light rounded text-text-muted hover:text-text"
        >
          <X size={18} />
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto">
        {activeTab === 'files' ? (
          <FilePreview file={filePreview} />
        ) : (
          <ToolHistory toolCalls={toolCalls} onConfirm={onConfirm} />
        )}
      </div>
    </aside>
  )
}
