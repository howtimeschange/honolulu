import { useState, useCallback, useRef, KeyboardEvent } from 'react'
import { Send, Paperclip, X, FileText, Loader2 } from 'lucide-react'
import type { Attachment } from '../../types'

interface InputBoxProps {
  onSend: (content: string, attachments?: Attachment[]) => void
  disabled?: boolean
}

const ACCEPTED_TYPES: Record<string, boolean> = {
  'image/png': true,
  'image/jpeg': true,
  'image/gif': true,
  'image/webp': true,
  'application/pdf': true,
}

const MAX_FILE_SIZE = 10 * 1024 * 1024 // 10MB

export function InputBox({ onSend, disabled }: InputBoxProps) {
  const [input, setInput] = useState('')
  const [attachments, setAttachments] = useState<Attachment[]>([])
  const [isUploading, setIsUploading] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleSend = useCallback(() => {
    const content = input.trim()
    if ((content || attachments.length > 0) && !disabled) {
      onSend(content, attachments.length > 0 ? attachments : undefined)
      setInput('')
      setAttachments([])
    }
  }, [input, attachments, disabled, onSend])

  const handleKeyDown = useCallback((e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }, [handleSend])

  const handleFileUpload = useCallback(async (files: FileList | null) => {
    if (!files || files.length === 0) return

    setIsUploading(true)
    try {
      for (const file of Array.from(files)) {
        // Validate file type
        if (!ACCEPTED_TYPES[file.type]) {
          alert(`Unsupported file type: ${file.type}. Supported: images (png, jpg, gif, webp) and PDF`)
          continue
        }

        // Validate file size
        if (file.size > MAX_FILE_SIZE) {
          alert(`File too large: ${file.name}. Maximum size: 10MB`)
          continue
        }

        // Upload to server
        const formData = new FormData()
        formData.append('file', file)

        const response = await fetch('/api/upload', {
          method: 'POST',
          body: formData,
        })

        if (!response.ok) {
          const error = await response.json()
          alert(`Upload failed: ${error.detail || 'Unknown error'}`)
          continue
        }

        const data = await response.json()

        // Add to attachments
        const attachment: Attachment = {
          id: data.id,
          type: data.type,
          filename: data.filename,
          contentType: data.content_type,
          base64: data.base64,
          text: data.text,
          pageCount: data.page_count,
        }
        setAttachments(prev => [...prev, attachment])
      }
    } catch (error) {
      console.error('Upload error:', error)
      alert('Failed to upload file')
    } finally {
      setIsUploading(false)
    }
  }, [])

  const handleRemoveAttachment = useCallback((id: string) => {
    setAttachments(prev => prev.filter(a => a.id !== id))
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    handleFileUpload(e.dataTransfer.files)
  }, [handleFileUpload])

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
  }, [])

  return (
    <div
      className="border-t border-border p-4"
      onDrop={handleDrop}
      onDragOver={handleDragOver}
    >
      {/* Attachment Previews */}
      {attachments.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-3 max-w-4xl mx-auto">
          {attachments.map((attachment) => (
            <div
              key={attachment.id}
              className="relative group flex items-center gap-2 bg-surface-light rounded-lg px-3 py-2 pr-8"
            >
              {attachment.type === 'image' ? (
                <>
                  <img
                    src={`data:${attachment.contentType};base64,${attachment.base64}`}
                    alt={attachment.filename}
                    className="w-10 h-10 object-cover rounded"
                  />
                  <span className="text-sm text-text-muted max-w-[100px] truncate">
                    {attachment.filename}
                  </span>
                </>
              ) : (
                <>
                  <FileText size={20} className="text-primary" />
                  <div className="flex flex-col">
                    <span className="text-sm text-text max-w-[100px] truncate">
                      {attachment.filename}
                    </span>
                    {attachment.pageCount && (
                      <span className="text-xs text-text-muted">
                        {attachment.pageCount} pages
                      </span>
                    )}
                  </div>
                </>
              )}
              <button
                onClick={() => handleRemoveAttachment(attachment.id)}
                className="absolute top-1 right-1 p-0.5 rounded-full bg-surface hover:bg-error/20 text-text-muted hover:text-error transition-colors"
              >
                <X size={14} />
              </button>
            </div>
          ))}
        </div>
      )}

      <div className="flex gap-3 items-end max-w-4xl mx-auto">
        {/* File Upload Button */}
        <input
          ref={fileInputRef}
          type="file"
          accept="image/png,image/jpeg,image/gif,image/webp,application/pdf"
          multiple
          onChange={(e) => {
            handleFileUpload(e.target.files)
            e.target.value = '' // Reset to allow selecting same file again
          }}
          className="hidden"
          disabled={disabled || isUploading}
        />
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          disabled={disabled || isUploading}
          className="p-3 text-text-muted hover:text-text hover:bg-surface-light rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          title="Upload file (images or PDF)"
        >
          {isUploading ? (
            <Loader2 size={20} className="animate-spin" />
          ) : (
            <Paperclip size={20} />
          )}
        </button>

        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={disabled ? 'Connecting...' : 'Type a message...'}
          disabled={disabled}
          rows={1}
          className="flex-1 resize-none bg-surface-light border border-border rounded-lg px-4 py-3 text-text placeholder-text-muted focus:outline-none focus:border-primary disabled:opacity-50"
          style={{ minHeight: '48px', maxHeight: '200px' }}
        />
        <button
          onClick={handleSend}
          disabled={disabled || (!input.trim() && attachments.length === 0)}
          className="p-3 bg-primary hover:bg-primary-dark disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg transition-colors"
        >
          <Send size={20} />
        </button>
      </div>
    </div>
  )
}
