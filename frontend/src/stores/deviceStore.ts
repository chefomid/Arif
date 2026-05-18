import { create } from 'zustand'

export interface AudioDeviceInfo {
  index: number
  name: string
  channels: number
  is_default: boolean
  selected: boolean
}

export interface CameraDeviceInfo {
  index: number
  name: string
  width: number
  height: number
  selected: boolean
}

interface DeviceState {
  micName: string
  cameraName: string
  audioDevices: AudioDeviceInfo[]
  cameraDevices: CameraDeviceInfo[]
  loading: boolean
  error: string | null
  fetchDevices: () => Promise<void>
  autoSelect: () => Promise<void>
  selectMic: (index: number | null) => Promise<void>
  selectCamera: (index: number) => Promise<void>
}

export const useDeviceStore = create<DeviceState>((set) => ({
  micName: '…',
  cameraName: '…',
  audioDevices: [],
  cameraDevices: [],
  loading: false,
  error: null,

  fetchDevices: async () => {
    set({ loading: true, error: null })
    try {
      const res = await fetch('/api/devices')
      if (!res.ok) throw new Error('Failed to load devices')
      const data = await res.json()
      set({
        micName: data.mic?.name ?? 'System default',
        cameraName: data.camera?.name ?? '—',
        audioDevices: data.audio_devices ?? [],
        cameraDevices: data.camera_devices ?? [],
        loading: false,
      })
    } catch (e) {
      set({ loading: false, error: e instanceof Error ? e.message : 'Unknown error' })
    }
  },

  autoSelect: async () => {
    set({ loading: true, error: null })
    try {
      const res = await fetch('/api/devices/auto', { method: 'POST' })
      if (!res.ok) throw new Error('Auto-select failed')
      const data = await res.json()
      set({
        micName: data.mic?.name ?? 'System default',
        cameraName: data.camera?.name ?? '—',
        audioDevices: data.audio_devices ?? [],
        cameraDevices: data.camera_devices ?? [],
        loading: false,
      })
    } catch (e) {
      set({ loading: false, error: e instanceof Error ? e.message : 'Unknown error' })
    }
  },

  selectMic: async (index: number | null) => {
    const res = await fetch('/api/devices/mic', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ index }),
    })
    if (!res.ok) throw new Error('Failed to set microphone')
    const data = await res.json()
    set({
      micName: data.mic?.name ?? 'System default',
      audioDevices: data.audio_devices ?? [],
    })
  },

  selectCamera: async (index: number) => {
    const res = await fetch('/api/devices/camera', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ index }),
    })
    if (!res.ok) throw new Error('Failed to set camera')
    const data = await res.json()
    set({
      cameraName: data.camera?.name ?? '—',
      cameraDevices: data.camera_devices ?? [],
    })
  },
}))
