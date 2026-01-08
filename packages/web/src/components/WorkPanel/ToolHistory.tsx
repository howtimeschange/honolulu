import { Check, X, Loader2, AlertCircle, Clock } from 'lucide-react'
import type { ToolCall } from '../../types'

interface ToolHistoryProps {
  toolCalls: ToolCall[]
  onConfirm: (toolCallId: string, action: 'allow' | 'deny' | 'allow_all') => void
}

function StatusIcon({ status }: { status: ToolCall['status'] }) {
  switch (status) {
    case 'completed':
      return <Check size={16} className="text-success" />
    case 'error':
      return <X size={16} className="text-error" />
    case 'running':
      return <Loader2 size={16} className="text-primary animate-spin" />
    case 'awaiting_confirmation':
      return <Clock size={16} className="text-warning" />
    default:
      return <AlertCircle size={16} className="text-text-muted" />
  }
}

export function ToolHistory({ toolCalls, onConfirm }: ToolHistoryProps) {
  if (toolCalls.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-text-muted p-4">
        <AlertCircle size={48} className="mb-4 opacity-50" />
        <p className="text-center">No tool executions yet</p>
        <p className="text-sm text-center mt-2">
          Tool calls will appear here as the agent works
        </p>
      </div>
    )
  }

  return (
    <div className="p-4 space-y-3">
      {toolCalls.map((toolCall) => (
        <div
          key={toolCall.id}
          className="bg-surface-light rounded-lg p-3"
        >
          {/* Header */}
          <div className="flex items-center gap-2 mb-2">
            <StatusIcon status={toolCall.status} />
            <span className="font-mono text-sm text-text">{toolCall.name}</span>
          </div>

          {/* Args */}
          <div className="text-xs text-text-muted mb-2 font-mono bg-surface rounded p-2 max-h-24 overflow-y-auto">
            {JSON.stringify(toolCall.args, null, 2)}
          </div>

          {/* Result */}
          {toolCall.result && (
            <div className="text-xs text-text-muted font-mono bg-surface rounded p-2 max-h-24 overflow-y-auto">
              {toolCall.result}
            </div>
          )}

          {/* Confirmation Buttons */}
          {toolCall.status === 'awaiting_confirmation' && (
            <div className="flex gap-2 mt-3">
              <button
                onClick={() => onConfirm(toolCall.id, 'allow')}
                className="flex-1 px-3 py-1.5 bg-success/20 hover:bg-success/30 text-success rounded text-sm transition-colors"
              >
                Allow
              </button>
              <button
                onClick={() => onConfirm(toolCall.id, 'allow_all')}
                className="flex-1 px-3 py-1.5 bg-primary/20 hover:bg-primary/30 text-primary rounded text-sm transition-colors"
              >
                Allow All
              </button>
              <button
                onClick={() => onConfirm(toolCall.id, 'deny')}
                className="flex-1 px-3 py-1.5 bg-error/20 hover:bg-error/30 text-error rounded text-sm transition-colors"
              >
                Deny
              </button>
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
