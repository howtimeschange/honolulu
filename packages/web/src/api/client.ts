import type { AppConfig, SubAgentInfo } from '../types'

const BASE_URL = '/api'

export interface StartChatOptions {
  message: string
  sessionId?: string
  multiAgent?: boolean
}

export async function startChat(options: StartChatOptions): Promise<{ session_id: string; ws_url: string }> {
  const response = await fetch(`${BASE_URL}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message: options.message,
      session_id: options.sessionId,
      multi_agent: options.multiAgent ?? false,
    }),
  })

  if (!response.ok) {
    throw new Error(`Failed to start chat: ${response.statusText}`)
  }

  return response.json()
}

export async function getConfig(): Promise<AppConfig> {
  const response = await fetch(`${BASE_URL}/config`)

  if (!response.ok) {
    throw new Error(`Failed to get config: ${response.statusText}`)
  }

  const data = await response.json()
  return {
    agentName: data.agent_name,
    model: data.model,
    routing: data.routing,
  }
}

export async function getTools(): Promise<Array<{ name: string; description: string }>> {
  const response = await fetch(`${BASE_URL}/tools`)

  if (!response.ok) {
    throw new Error(`Failed to get tools: ${response.statusText}`)
  }

  return response.json()
}

export async function listSessions(): Promise<Array<{ id: string; created_at: string; status: string }>> {
  const response = await fetch(`${BASE_URL}/sessions`)

  if (!response.ok) {
    throw new Error(`Failed to list sessions: ${response.statusText}`)
  }

  return response.json()
}

export async function deleteSession(sessionId: string): Promise<void> {
  const response = await fetch(`${BASE_URL}/sessions/${sessionId}`, {
    method: 'DELETE',
  })

  if (!response.ok) {
    throw new Error(`Failed to delete session: ${response.statusText}`)
  }
}

export async function getAgents(): Promise<{ agents: SubAgentInfo[] }> {
  const response = await fetch(`${BASE_URL}/agents`)

  if (!response.ok) {
    throw new Error(`Failed to get agents: ${response.statusText}`)
  }

  return response.json()
}
