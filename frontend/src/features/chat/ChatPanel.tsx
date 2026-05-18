import { useEffect, useRef, useState } from 'react'
import { wsClient } from '../../lib/wsClient'
import { useChatStore } from '../../stores/chatStore'
import { useUiStore } from '../../stores/uiStore'
import './ChatPanel.css'

export function ChatPanel() {
  const messages = useChatStore((s) => s.messages)
  const isStreaming = useChatStore((s) => s.isStreaming)
  const partialTranscript = useChatStore((s) => s.partialTranscript)
  const addMessage = useChatStore((s) => s.addMessage)
  const micHot = useUiStore((s) => s.micHot)
  const [input, setInput] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, partialTranscript])

  const send = () => {
    const text = input.trim()
    if (!text || isStreaming) return
    addMessage('user', text)
    wsClient.send('chat_send', { text })
    setInput('')
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send()
    }
  }

  return (
    <div className="chat-panel">
      <div className="terminal-banner">
        <span className="banner-comment">
          # Press ? for keys · D devices · C camera · / to type
        </span>
      </div>

      <div className="messages">
        {messages.length === 0 && !partialTranscript && (
          <div className="message system">
            <p>Ready. Type below or hold Space to speak.</p>
          </div>
        )}
        {messages.map((m) => (
          <div key={m.id} className={`message ${m.role}`}>
            <p>{m.content}</p>
          </div>
        ))}
        {partialTranscript && (
          <div className={`message user partial ${micHot ? 'recording' : ''}`}>
            <p>{partialTranscript}</p>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="input-row">
        <textarea
          id="chat-input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Enter command or message…"
          rows={2}
          disabled={isStreaming}
        />
        <button onClick={send} disabled={isStreaming || !input.trim()}>
          Send
        </button>
      </div>
    </div>
  )
}
