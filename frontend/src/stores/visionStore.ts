import { create } from 'zustand'

export interface Detection {
  class_name: string
  confidence: number
  x: number
  y: number
  w: number
  h: number
}

interface VisionState {
  detections: Detection[]
  frameWidth: number
  frameHeight: number
  lastTs: number
  setFrameMeta: (detections: Detection[], w: number, h: number, ts: number) => void
}

export const useVisionStore = create<VisionState>((set) => ({
  detections: [],
  frameWidth: 0,
  frameHeight: 0,
  lastTs: 0,

  setFrameMeta: (detections, frameWidth, frameHeight, lastTs) =>
    set({ detections, frameWidth, frameHeight, lastTs }),
}))
