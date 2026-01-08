import ReactMarkdown from 'react-markdown'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { User, Bot, FileText } from 'lucide-react'
import type { Message, Attachment } from '../../types'

interface MessageBubbleProps {
  message: Message
  isStreaming?: boolean
}

function AttachmentPreview({ attachment }: { attachment: Attachment }) {
  if (attachment.type === 'image') {
    return (
      <div className="mt-2">
        <img
          src={`data:${attachment.contentType};base64,${attachment.base64}`}
          alt={attachment.filename}
          className="max-w-[300px] max-h-[300px] rounded-lg object-contain"
        />
      </div>
    )
  }

  return (
    <div className="mt-2 flex items-center gap-2 bg-surface-lighter rounded-lg px-3 py-2">
      <FileText size={20} className="text-primary" />
      <div className="flex flex-col">
        <span className="text-sm text-text">{attachment.filename}</span>
        {attachment.pageCount && (
          <span className="text-xs text-text-muted">
            {attachment.pageCount} pages
          </span>
        )}
      </div>
    </div>
  )
}

export function MessageBubble({ message, isStreaming = false }: MessageBubbleProps) {
  const isUser = message.role === 'user'
  const hasAttachments = message.attachments && message.attachments.length > 0

  return (
    <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : ''}`}>
      {/* Avatar */}
      <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
        isUser ? 'bg-primary' : 'bg-surface-lighter'
      }`}>
        {isUser ? <User size={16} /> : <Bot size={16} />}
      </div>

      {/* Content */}
      <div className={`flex-1 max-w-[80%] ${isUser ? 'text-right' : ''}`}>
        {message.subAgent && (
          <div className="text-xs text-text-muted mb-1">
            via {message.subAgent}
          </div>
        )}
        <div className={`inline-block rounded-lg px-4 py-2 ${
          isUser
            ? 'bg-primary text-white'
            : 'bg-surface-light text-text'
        }`}>
          {/* Attachments (for user messages) */}
          {hasAttachments && isUser && (
            <div className={`mb-2 ${isUser ? 'text-left' : ''}`}>
              {message.attachments!.map((attachment) => (
                <AttachmentPreview key={attachment.id} attachment={attachment} />
              ))}
            </div>
          )}

          <div className="prose prose-invert prose-sm max-w-none">
            <ReactMarkdown
              components={{
                code({ className, children, ...props }) {
                  const match = /language-(\w+)/.exec(className || '')
                  const isInline = !match

                  if (isInline) {
                    return (
                      <code className="bg-surface-lighter px-1 py-0.5 rounded text-sm" {...props}>
                        {children}
                      </code>
                    )
                  }

                  return (
                    <SyntaxHighlighter
                      style={oneDark}
                      language={match[1]}
                      PreTag="div"
                      customStyle={{
                        margin: '0.5rem 0',
                        borderRadius: '0.375rem',
                        fontSize: '0.875rem',
                      }}
                    >
                      {String(children).replace(/\n$/, '')}
                    </SyntaxHighlighter>
                  )
                },
              }}
            >
              {message.content}
            </ReactMarkdown>
            {isStreaming && (
              <span className="inline-block w-2 h-4 ml-0.5 bg-primary animate-pulse" />
            )}
          </div>
        </div>
        {!isStreaming && (
          <div className="text-xs text-text-muted mt-1">
            {message.timestamp.toLocaleTimeString()}
          </div>
        )}
      </div>
    </div>
  )
}
