/** Stub for future mouse/gesture routing (e.g. click detection bbox to ask). */

export type InputEvent =
  | { kind: 'click'; x: number; y: number; target?: string }
  | { kind: 'key'; code: string; action: 'down' | 'up' }

const listeners: Array<(ev: InputEvent) => void> = []

export function onInput(handler: (ev: InputEvent) => void): () => void {
  listeners.push(handler)
  return () => {
    const i = listeners.indexOf(handler)
    if (i >= 0) listeners.splice(i, 1)
  }
}

export function emitInput(ev: InputEvent): void {
  listeners.forEach((h) => h(ev))
}
