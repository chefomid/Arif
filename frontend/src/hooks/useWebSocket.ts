import { useEffect } from 'react'
import { wsClient, type WsMessage } from '../lib/wsClient'
import { useChatStore } from '../stores/chatStore'
import { useUiStore } from '../stores/uiStore'
import { useVisionStore } from '../stores/visionStore'
import type { Detection } from '../stores/visionStore'

let streamingMsgId: string | null = null

export function useWebSocket() {
  const addMessage = useChatStore((s) => s.addMessage)
  const appendToMessage = useChatStore((s) => s.appendToMessage)
  const finishStreaming = useChatStore((s) => s.finishStreaming)
  const setPartialTranscript = useChatStore((s) => s.setPartialTranscript)
  const clearPartialTranscript = useChatStore((s) => s.clearPartialTranscript)
  const setWsConnected = useUiStore((s) => s.setWsConnected)
  const setFrameMeta = useVisionStore((s) => s.setFrameMeta)

  useEffect(() => {
    wsClient.connect()

    const unsub = wsClient.subscribe((msg: WsMessage) => {
      switch (msg.type) {
        case 'stt_partial':
          setPartialTranscript((msg.payload.text as string) || '')
          break

        case 'stt_final': {
          const text = (msg.payload.text as string) || ''
          const autoSend = msg.payload.auto_send as boolean
          if (autoSend && text) {
            addMessage('user', text)
            clearPartialTranscript()
          } else {
            setPartialTranscript(text)
          }
          break
        }

        case 'chat_token': {
          const token = (msg.payload.token as string) || ''
          if (!streamingMsgId) {
            streamingMsgId = addMessage('assistant', '')
            useChatStore.setState({ isStreaming: true })
          }
          if (streamingMsgId) appendToMessage(streamingMsgId, token)
          break
        }

        case 'chat_done':
          streamingMsgId = null
          finishStreaming()
          clearPartialTranscript()
          break

        case 'vision_frame_meta':
          setFrameMeta(
            (msg.payload.detections as Detection[]) || [],
            (msg.payload.frame_width as number) || 0,
            (msg.payload.frame_height as number) || 0,
            (msg.payload.ts as number) || 0
          )
          break

        case 'error':
          console.error('WS error:', msg.payload.message)
          break
      }
    })

    const checkConnection = setInterval(() => {
      setWsConnected(wsClient.connected)
    }, 1000)

    return () => {
      unsub()
      clearInterval(checkConnection)
      wsClient.disconnect()
    }
  }, [
    addMessage,
    appendToMessage,
    finishStreaming,
    setPartialTranscript,
    clearPartialTranscript,
    setWsConnected,
    setFrameMeta,
  ])

  return wsClient
}
