import { MessageList } from './MessageList'
import { InputBox } from './InputBox'
import type { Message, Attachment } from '../../types'
import { MessageSquarePlus } from 'lucide-react'

interface ChatPanelProps {
  messages: Message[]
  streamingMessage?: string
  isStreaming?: boolean
  onSendMessage: (content: string, attachments?: Attachment[]) => void
  isConnected: boolean
  hasSession: boolean
  onNewSession: () => void
}

export function ChatPanel({
  messages,
  streamingMessage = '',
  isStreaming = false,
  onSendMessage,
  isConnected,
  hasSession,
  onNewSession,
}: ChatPanelProps) {
  if (!hasSession) {
    return (
      <main className="flex-1 flex flex-col items-center justify-center bg-surface">
        <div className="text-center">
          <h2 className="text-2xl font-semibold text-text mb-2">Welcome to Honolulu</h2>
          <p className="text-text-muted mb-6">Start a new chat to begin</p>
          <button
            onClick={onNewSession}
            className="flex items-center gap-2 px-6 py-3 bg-primary hover:bg-primary-dark text-white rounded-lg transition-colors"
          >
            <MessageSquarePlus size={20} />
            <span>New Chat</span>
          </button>
        </div>
      </main>
    )
  }

  return (
    <main className="flex-1 flex flex-col bg-surface">
      <MessageList
        messages={messages}
        streamingMessage={streamingMessage}
        isStreaming={isStreaming}
      />
      <InputBox onSend={onSendMessage} disabled={!isConnected || isStreaming} />
    </main>
  )
}
