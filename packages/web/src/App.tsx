import { useState, useCallback, useEffect, useRef } from 'react'
import { Settings } from 'lucide-react'
import { Sidebar } from './components/Sidebar'
import { ChatPanel } from './components/ChatPanel'
import { WorkPanel } from './components/WorkPanel'
import { StatusBar } from './components/StatusBar'
import { SettingsModal } from './components/Settings'
import { useSession } from './hooks/useSession'
import {
  saveSessionMessages,
  loadSessionMessages,
  saveSessions,
  loadSessions,
  saveCurrentSessionId,
  loadCurrentSessionId,
  generateSessionTitle,
} from './utils/storage'
import type { Session, Message, ToolCall, SubAgentStatus, FilePreview, Attachment } from './types'

function App() {
  // Load persisted state on mount
  const [sessions, setSessions] = useState<Session[]>(() => loadSessions())
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(() => loadCurrentSessionId())
  const [messages, setMessages] = useState<Message[]>(() => {
    const savedSessionId = loadCurrentSessionId()
    if (savedSessionId) {
      return loadSessionMessages(savedSessionId) || []
    }
    return []
  })
  const [toolCalls, setToolCalls] = useState<ToolCall[]>([])

  // Track previous session ID for saving messages before switch
  const prevSessionIdRef = useRef<string | null>(currentSessionId)
  const [subAgents, setSubAgents] = useState<SubAgentStatus[]>([
    { name: 'main', displayName: 'Main Agent', status: 'idle' },
    { name: 'coder', displayName: 'Coder', status: 'idle' },
    { name: 'researcher', displayName: 'Researcher', status: 'idle' },
  ])
  const [filePreview, _setFilePreview] = useState<FilePreview | null>(null)
  const [isWorkPanelOpen, setIsWorkPanelOpen] = useState(true)
  const [isSettingsOpen, setIsSettingsOpen] = useState(false)

  // Streaming message state
  const [streamingMessage, setStreamingMessage] = useState<string>('')
  const [isStreaming, setIsStreaming] = useState(false)
  const streamingMessageIdRef = useRef<string | null>(null)

  const { isConnected, sendMessage, sendConfirmation, config } = useSession({
    sessionId: currentSessionId,
    onMessage: useCallback((msg) => {
      if (msg.type === 'text_delta') {
        // Accumulate streaming text
        if (!isStreaming) {
          setIsStreaming(true)
          streamingMessageIdRef.current = crypto.randomUUID()
        }
        setStreamingMessage(prev => prev + (msg.content || ''))
      } else if (msg.type === 'text') {
        // Complete message (fallback for non-streaming)
        setMessages(prev => [...prev, {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: msg.content || '',
          timestamp: new Date(),
        }])
      } else if (msg.type === 'done') {
        // Finalize streaming message
        if (isStreaming && streamingMessage) {
          setMessages(prev => [...prev, {
            id: streamingMessageIdRef.current || crypto.randomUUID(),
            role: 'assistant',
            content: streamingMessage,
            timestamp: new Date(),
          }])
          setStreamingMessage('')
          setIsStreaming(false)
          streamingMessageIdRef.current = null
        }
      } else if (msg.type === 'tool_call') {
        setToolCalls(prev => [...prev, {
          id: msg.id || crypto.randomUUID(),
          name: msg.tool || 'unknown',
          args: msg.args || {},
          status: msg.requires_confirmation ? 'awaiting_confirmation' : 'running',
        }])
      } else if (msg.type === 'tool_result') {
        setToolCalls(prev => prev.map(tc =>
          tc.name === msg.tool ? { ...tc, status: 'completed', result: String(msg.content) } : tc
        ))
      } else if (msg.type === 'sub_agent_start') {
        setSubAgents(prev => prev.map(sa =>
          sa.name === msg.agent ? { ...sa, status: 'running', currentTask: msg.task } : sa
        ))
      } else if (msg.type === 'sub_agent_done') {
        setSubAgents(prev => prev.map(sa =>
          sa.name === msg.agent ? { ...sa, status: 'completed', currentTask: undefined } : sa
        ))
      } else if (msg.type === 'error') {
        // Reset streaming state on error
        setStreamingMessage('')
        setIsStreaming(false)
        streamingMessageIdRef.current = null
      }
    }, [isStreaming, streamingMessage]),
    onError: useCallback((error) => {
      console.error('WebSocket error:', error)
      // Reset streaming state on error
      setStreamingMessage('')
      setIsStreaming(false)
    }, []),
  })

  const handleNewSession = useCallback(async () => {
    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: '' }),
      })
      const data = await response.json()
      const newSession: Session = {
        id: data.session_id,
        createdAt: new Date().toISOString(),
        status: 'active',
        title: 'New Chat',
      }
      setSessions(prev => [newSession, ...prev])
      setCurrentSessionId(data.session_id)
      setMessages([])
      setToolCalls([])
    } catch (error) {
      console.error('Failed to create session:', error)
    }
  }, [])

  const handleSendMessage = useCallback((content: string, attachments?: Attachment[]) => {
    setMessages(prev => [...prev, {
      id: crypto.randomUUID(),
      role: 'user',
      content,
      timestamp: new Date(),
      attachments,
    }])
    sendMessage(content, attachments)
  }, [sendMessage])

  const handleConfirm = useCallback((toolCallId: string, action: 'allow' | 'deny' | 'allow_all') => {
    sendConfirmation(toolCallId, action)
    setToolCalls(prev => prev.map(tc =>
      tc.id === toolCallId ? { ...tc, status: action === 'deny' ? 'error' : 'running' } : tc
    ))
  }, [sendConfirmation])

  // Handle session switch - save current messages before switching, load new messages after
  const handleSelectSession = useCallback((newSessionId: string) => {
    // Save current session messages before switching
    if (prevSessionIdRef.current && prevSessionIdRef.current !== newSessionId) {
      saveSessionMessages(prevSessionIdRef.current, messages)
    }

    // Load messages for the new session
    const loadedMessages = loadSessionMessages(newSessionId)
    setMessages(loadedMessages || [])
    setToolCalls([])
    setCurrentSessionId(newSessionId)
    prevSessionIdRef.current = newSessionId
  }, [messages])

  // Persist sessions list when it changes
  useEffect(() => {
    saveSessions(sessions)
  }, [sessions])

  // Persist current session ID when it changes
  useEffect(() => {
    saveCurrentSessionId(currentSessionId)
  }, [currentSessionId])

  // Persist messages when they change (debounced via the messages array)
  useEffect(() => {
    if (currentSessionId && messages.length > 0) {
      saveSessionMessages(currentSessionId, messages)

      // Update session title based on first message
      const title = generateSessionTitle(messages)
      setSessions(prev => prev.map(s =>
        s.id === currentSessionId ? { ...s, title } : s
      ))
    }
  }, [currentSessionId, messages])

  return (
    <div className="h-screen flex flex-col bg-surface">
      {/* Header */}
      <header className="h-12 border-b border-border flex items-center justify-between px-4">
        <h1 className="text-lg font-semibold text-text">Honolulu</h1>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsSettingsOpen(true)}
            className="flex items-center gap-2 p-2 hover:bg-surface-light rounded text-text-muted hover:text-text"
          >
            <Settings size={18} />
            Settings
          </button>
        </div>
      </header>

      {/* Settings Modal */}
      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
      />

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar */}
        <Sidebar
          sessions={sessions}
          currentSessionId={currentSessionId}
          subAgents={subAgents}
          onSelectSession={handleSelectSession}
          onNewSession={handleNewSession}
        />

        {/* Chat Panel */}
        <ChatPanel
          messages={messages}
          streamingMessage={streamingMessage}
          isStreaming={isStreaming}
          onSendMessage={handleSendMessage}
          isConnected={isConnected}
          hasSession={!!currentSessionId}
          onNewSession={handleNewSession}
        />

        {/* Work Panel */}
        {isWorkPanelOpen && (
          <WorkPanel
            toolCalls={toolCalls}
            filePreview={filePreview}
            onConfirm={handleConfirm}
            onClose={() => setIsWorkPanelOpen(false)}
          />
        )}
      </div>

      {/* Status Bar */}
      <StatusBar
        isConnected={isConnected}
        hasSession={!!currentSessionId}
        model={config?.model}
        onToggleWorkPanel={() => setIsWorkPanelOpen(!isWorkPanelOpen)}
        isWorkPanelOpen={isWorkPanelOpen}
      />
    </div>
  )
}

export default App
