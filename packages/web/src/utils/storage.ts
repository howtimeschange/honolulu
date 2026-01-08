import type { Message, Session } from '../types'

const STORAGE_PREFIX = 'honolulu_'
const SESSION_MESSAGES_KEY = (id: string) => `${STORAGE_PREFIX}messages_${id}`
const SESSIONS_KEY = `${STORAGE_PREFIX}sessions`
const CURRENT_SESSION_KEY = `${STORAGE_PREFIX}current_session`

/**
 * Save messages for a session to localStorage
 */
export function saveSessionMessages(sessionId: string, messages: Message[]): void {
  try {
    // Convert Date objects to ISO strings for serialization
    const serializable = messages.map(msg => ({
      ...msg,
      timestamp: msg.timestamp instanceof Date ? msg.timestamp.toISOString() : msg.timestamp,
    }))
    localStorage.setItem(SESSION_MESSAGES_KEY(sessionId), JSON.stringify(serializable))
  } catch (error) {
    console.error('Failed to save messages to localStorage:', error)
    // If storage is full, try to clean up old sessions
    if (error instanceof DOMException && error.name === 'QuotaExceededError') {
      cleanupOldSessions()
    }
  }
}

/**
 * Load messages for a session from localStorage
 */
export function loadSessionMessages(sessionId: string): Message[] | null {
  try {
    const data = localStorage.getItem(SESSION_MESSAGES_KEY(sessionId))
    if (!data) return null

    const messages = JSON.parse(data) as Message[]
    // Convert ISO strings back to Date objects
    return messages.map(msg => ({
      ...msg,
      timestamp: new Date(msg.timestamp),
    }))
  } catch (error) {
    console.error('Failed to load messages from localStorage:', error)
    return null
  }
}

/**
 * Delete messages for a session
 */
export function deleteSessionMessages(sessionId: string): void {
  try {
    localStorage.removeItem(SESSION_MESSAGES_KEY(sessionId))
  } catch (error) {
    console.error('Failed to delete messages from localStorage:', error)
  }
}

/**
 * Save sessions list to localStorage
 */
export function saveSessions(sessions: Session[]): void {
  try {
    localStorage.setItem(SESSIONS_KEY, JSON.stringify(sessions))
  } catch (error) {
    console.error('Failed to save sessions to localStorage:', error)
  }
}

/**
 * Load sessions list from localStorage
 */
export function loadSessions(): Session[] {
  try {
    const data = localStorage.getItem(SESSIONS_KEY)
    if (!data) return []
    return JSON.parse(data) as Session[]
  } catch (error) {
    console.error('Failed to load sessions from localStorage:', error)
    return []
  }
}

/**
 * Save current session ID
 */
export function saveCurrentSessionId(sessionId: string | null): void {
  try {
    if (sessionId) {
      localStorage.setItem(CURRENT_SESSION_KEY, sessionId)
    } else {
      localStorage.removeItem(CURRENT_SESSION_KEY)
    }
  } catch (error) {
    console.error('Failed to save current session to localStorage:', error)
  }
}

/**
 * Load current session ID
 */
export function loadCurrentSessionId(): string | null {
  try {
    return localStorage.getItem(CURRENT_SESSION_KEY)
  } catch (error) {
    console.error('Failed to load current session from localStorage:', error)
    return null
  }
}

/**
 * Clean up old sessions to free storage space
 * Keeps the 10 most recent sessions
 */
function cleanupOldSessions(): void {
  try {
    const sessions = loadSessions()
    if (sessions.length <= 10) return

    // Sort by createdAt descending and keep only the 10 most recent
    const sortedSessions = sessions.sort(
      (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
    )
    const sessionsToKeep = sortedSessions.slice(0, 10)
    const sessionsToDelete = sortedSessions.slice(10)

    // Delete old session messages
    sessionsToDelete.forEach(session => {
      deleteSessionMessages(session.id)
    })

    // Update sessions list
    saveSessions(sessionsToKeep)

    console.log(`Cleaned up ${sessionsToDelete.length} old sessions`)
  } catch (error) {
    console.error('Failed to cleanup old sessions:', error)
  }
}

/**
 * Generate a title from the first user message
 */
export function generateSessionTitle(messages: Message[]): string {
  const firstUserMessage = messages.find(m => m.role === 'user')
  if (!firstUserMessage) return 'New Chat'

  const content = firstUserMessage.content.trim()
  if (content.length <= 30) return content
  return content.slice(0, 30) + '...'
}
