export type WsMessageType =
  | 'ptt_start'
  | 'ptt_end'
  | 'chat_send'
  | 'camera_subscribe'
  | 'camera_unsubscribe'
  | 'stt_partial'
  | 'stt_final'
  | 'chat_token'
  | 'chat_done'
  | 'vision_frame_meta'
  | 'error'
  | 'pong'

export interface WsMessage {
  v: number
  type: WsMessageType
  payload: Record<string, unknown>
}

type MessageHandler = (msg: WsMessage) => void

export class WsClient {
  private ws: WebSocket | null = null
  private handlers: Set<MessageHandler> = new Set()
  private reconnectTimer: number | null = null
  private url: string

  constructor(url?: string) {
    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const host = window.location.host
    this.url = url ?? `${proto}://${host}/ws`
  }

  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN) return

    this.ws = new WebSocket(this.url)

    this.ws.onopen = () => {
      if (this.reconnectTimer) {
        clearTimeout(this.reconnectTimer)
        this.reconnectTimer = null
      }
    }

    this.ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data) as WsMessage
        this.handlers.forEach((h) => h(msg))
      } catch {
        console.error('Invalid WS message')
      }
    }

    this.ws.onclose = () => {
      this.reconnectTimer = window.setTimeout(() => this.connect(), 3000)
    }

    this.ws.onerror = () => {
      this.ws?.close()
    }
  }

  disconnect(): void {
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer)
    this.ws?.close()
    this.ws = null
  }

  subscribe(handler: MessageHandler): () => void {
    this.handlers.add(handler)
    return () => this.handlers.delete(handler)
  }

  send(type: WsMessageType, payload: Record<string, unknown> = {}): void {
    if (this.ws?.readyState !== WebSocket.OPEN) {
      console.warn('WebSocket not connected')
      return
    }
    this.ws.send(JSON.stringify({ v: 1, type, payload }))
  }

  get connected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN
  }
}

export const wsClient = new WsClient()
