import { useState, useEffect } from 'react'
import { useWebSocket } from './useWebSocket'
import { getConfig, getAgents } from '../api/client'
import type { AgentMessage, AppConfig, SubAgentInfo, SubAgentStatus } from '../types'

interface UseSessionOptions {
  sessionId: string | null
  onMessage: (message: AgentMessage) => void
  onError: (error: Error) => void
  onSubAgentUpdate?: (status: SubAgentStatus) => void
}

export function useSession({ sessionId, onMessage, onError, onSubAgentUpdate }: UseSessionOptions) {
  const [config, setConfig] = useState<AppConfig | null>(null)
  const [agents, setAgents] = useState<SubAgentInfo[]>([])

  // Wrap onMessage to handle sub-agent events
  const handleMessage = (message: AgentMessage) => {
    // Handle sub-agent events
    if (message.type.startsWith('sub_agent_') && onSubAgentUpdate && message.agent) {
      const eventType = message.type.replace('sub_agent_', '')
      let status: SubAgentStatus['status'] = 'idle'

      if (eventType === 'start') {
        status = 'running'
      } else if (eventType === 'done') {
        status = 'completed'
      } else if (eventType === 'progress') {
        status = 'running'
      }

      onSubAgentUpdate({
        name: message.agent,
        displayName: agents.find((a) => a.name === message.agent)?.display_name || message.agent,
        status,
        currentTask: message.content,
      })
    }

    // Forward to original handler
    onMessage(message)
  }

  const { isConnected, sendMessage, sendConfirmation, cancel } = useWebSocket({
    sessionId,
    onMessage: handleMessage,
    onError,
  })

  useEffect(() => {
    getConfig()
      .then(setConfig)
      .catch((error) => console.error('Failed to load config:', error))

    getAgents()
      .then((data) => setAgents(data.agents))
      .catch((error) => console.error('Failed to load agents:', error))
  }, [])

  return {
    isConnected,
    sendMessage,
    sendConfirmation,
    cancel,
    config,
    agents,
  }
}
