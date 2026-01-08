import { MessageSquare } from 'lucide-react'
import type { Session } from '../../types'

interface SessionListProps {
  sessions: Session[]
  currentSessionId: string | null
  onSelect: (id: string) => void
}

export function SessionList({ sessions, currentSessionId, onSelect }: SessionListProps) {
  if (sessions.length === 0) {
    return (
      <div className="text-text-muted text-sm py-4 text-center">
        No sessions yet
      </div>
    )
  }

  return (
    <div className="space-y-1">
      {sessions.map((session) => (
        <button
          key={session.id}
          onClick={() => onSelect(session.id)}
          className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-left transition-colors ${
            currentSessionId === session.id
              ? 'bg-surface-light text-text'
              : 'text-text-muted hover:bg-surface-light hover:text-text'
          }`}
        >
          <MessageSquare size={16} />
          <span className="truncate text-sm">{session.title || 'Untitled'}</span>
        </button>
      ))}
    </div>
  )
}
