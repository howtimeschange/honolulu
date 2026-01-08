import { useEffect, useRef, useState, useCallback } from 'react'
import type { AgentMessage, Attachment } from '../types'

interface UseWebSocketOptions {
  sessionId: string | null
  onMessage: (message: AgentMessage) => void
  onError: (error: Error) => void
  onClose?: () => void
}

export function useWebSocket({ sessionId, onMessage, onError, onClose }: UseWebSocketOptions) {
  const [isConnected, setIsConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<number | null>(null)

  // Use refs to avoid callback dependency issues
  const onMessageRef = useRef(onMessage)
  const onErrorRef = useRef(onError)
  const onCloseRef = useRef(onClose)

  // Update refs when callbacks change
  useEffect(() => {
    onMessageRef.current = onMessage
    onErrorRef.current = onError
    onCloseRef.current = onClose
  }, [onMessage, onError, onClose])

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
    setIsConnected(false)
  }, [])

  const sendMessage = useCallback((content: string, attachments?: Attachment[]) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      const message: Record<string, unknown> = {
        type: 'message',
        content,
      }
      if (attachments && attachments.length > 0) {
        message.attachments = attachments
      }
      wsRef.current.send(JSON.stringify(message))
    } else {
      console.error('WebSocket is not connected')
    }
  }, [])

  const sendConfirmation = useCallback((
    toolCallId: string,
    action: 'allow' | 'deny' | 'allow_all',
    toolName?: string
  ) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'confirm_response',
        id: toolCallId,
        action,
        tool_name: toolName,
      }))
    }
  }, [])

  const cancel = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'cancel' }))
    }
  }, [])

  useEffect(() => {
    if (!sessionId) return

    // Cleanup any existing connection first
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/ws/${sessionId}`

    console.log('Connecting to WebSocket:', wsUrl)
    const ws = new WebSocket(wsUrl)

    ws.onopen = () => {
      setIsConnected(true)
      console.log('WebSocket connected')
    }

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data) as AgentMessage
        onMessageRef.current(message)
      } catch (error) {
        onErrorRef.current(new Error(`Failed to parse message: ${error}`))
      }
    }

    ws.onerror = (event) => {
      console.error('WebSocket error:', event)
      onErrorRef.current(new Error('WebSocket connection error'))
    }

    ws.onclose = () => {
      setIsConnected(false)
      console.log('WebSocket closed')
      onCloseRef.current?.()
    }

    wsRef.current = ws

    return () => {
      if (wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
      }
    }
  }, [sessionId]) // Only depend on sessionId

  return {
    isConnected,
    sendMessage,
    sendConfirmation,
    cancel,
    disconnect,
  }
}
