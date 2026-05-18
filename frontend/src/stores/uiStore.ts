import { create } from 'zustand'

export type View = 'chat' | 'camera' | 'devices' | 'help'

interface UiState {
  view: View
  wsConnected: boolean
  llmHealthy: boolean
  micHot: boolean
  setView: (view: View) => void
  toggleCamera: () => void
  openDevices: () => void
  openHelp: () => void
  goToChat: () => void
  setWsConnected: (v: boolean) => void
  setLlmHealthy: (v: boolean) => void
  setMicHot: (v: boolean) => void
}

export const useUiStore = create<UiState>((set, get) => ({
  view: 'chat',
  wsConnected: false,
  llmHealthy: false,
  micHot: false,

  setView: (view) => set({ view }),

  toggleCamera: () => {
    const v = get().view
    set({ view: v === 'camera' ? 'chat' : 'camera' })
  },

  openDevices: () => set({ view: 'devices' }),

  openHelp: () => set({ view: 'help' }),

  goToChat: () => set({ view: 'chat' }),

  setWsConnected: (v) => set({ wsConnected: v }),
  setLlmHealthy: (v) => set({ llmHealthy: v }),
  setMicHot: (v) => set({ micHot: v }),
}))
