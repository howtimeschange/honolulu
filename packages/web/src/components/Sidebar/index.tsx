import { SessionList } from './SessionList'
import { AgentStatus } from './AgentStatus'
import type { Session, SubAgentStatus } from '../../types'
import { Plus } from 'lucide-react'

interface SidebarProps {
  sessions: Session[]
  currentSessionId: string | null
  subAgents: SubAgentStatus[]
  onSelectSession: (id: string) => void
  onNewSession: () => void
}

export function Sidebar({
  sessions,
  currentSessionId,
  subAgents,
  onSelectSession,
  onNewSession,
}: SidebarProps) {
  return (
    <aside className="w-56 border-r border-border flex flex-col bg-surface">
      {/* New Chat Button */}
      <div className="p-3">
        <button
          onClick={onNewSession}
          className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-primary hover:bg-primary-dark text-white rounded-lg transition-colors"
        >
          <Plus size={18} />
          <span>New Chat</span>
        </button>
      </div>

      {/* Sessions */}
      <div className="flex-1 overflow-y-auto">
        <div className="px-3 py-2">
          <h3 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-2">
            Sessions
          </h3>
          <SessionList
            sessions={sessions}
            currentSessionId={currentSessionId}
            onSelect={onSelectSession}
          />
        </div>
      </div>

      {/* Agent Status */}
      <div className="border-t border-border p-3">
        <h3 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-2">
          Agents
        </h3>
        <AgentStatus agents={subAgents} />
      </div>
    </aside>
  )
}
