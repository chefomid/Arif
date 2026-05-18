import { create } from 'zustand'

export interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  streaming?: boolean
}

interface ChatState {
  messages: Message[]
  isStreaming: boolean
  partialTranscript: string
  addMessage: (role: Message['role'], content: string) => string
  appendToMessage: (id: string, token: string) => void
  finishStreaming: () => void
  setPartialTranscript: (text: string) => void
  clearPartialTranscript: () => void
}

let idCounter = 0
const nextId = () => `msg-${++idCounter}`

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  isStreaming: false,
  partialTranscript: '',

  addMessage: (role, content) => {
    const id = nextId()
    set((s) => ({
      messages: [...s.messages, { id, role, content }],
    }))
    return id
  },

  appendToMessage: (id, token) => {
    set((s) => ({
      messages: s.messages.map((m) =>
        m.id === id ? { ...m, content: m.content + token } : m
      ),
    }))
  },

  finishStreaming: () => set({ isStreaming: false }),

  setPartialTranscript: (text) => set({ partialTranscript: text }),

  clearPartialTranscript: () => set({ partialTranscript: '' }),
}))
