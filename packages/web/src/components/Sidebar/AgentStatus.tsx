import type { SubAgentStatus } from '../../types'

interface AgentStatusProps {
  agents: SubAgentStatus[]
}

function StatusIcon({ status }: { status: SubAgentStatus['status'] }) {
  const colors = {
    idle: 'bg-text-muted',
    running: 'bg-success animate-pulse',
    completed: 'bg-primary',
  }

  return (
    <span className={`w-2 h-2 rounded-full ${colors[status]}`} />
  )
}

export function AgentStatus({ agents }: AgentStatusProps) {
  return (
    <div className="space-y-2">
      {agents.map((agent) => (
        <div
          key={agent.name}
          className="flex items-center gap-2 text-sm"
        >
          <StatusIcon status={agent.status} />
          <span className={agent.status === 'running' ? 'text-text' : 'text-text-muted'}>
            {agent.displayName}
          </span>
          {agent.currentTask && (
            <span className="text-xs text-text-muted truncate ml-auto">
              {agent.currentTask}
            </span>
          )}
        </div>
      ))}
    </div>
  )
}
