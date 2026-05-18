import { useEffect } from 'react'

export function useKeyboardHold(
  key: string,
  onDown: () => void,
  onUp: () => void,
  enabled = true
) {
  useEffect(() => {
    if (!enabled) return

    const isTypingTarget = () => {
      const el = document.activeElement
      if (!el) return false
      const tag = el.tagName
      return (
        tag === 'INPUT' ||
        tag === 'TEXTAREA' ||
        (el instanceof HTMLElement && el.isContentEditable)
      )
    }

    const handleDown = (e: KeyboardEvent) => {
      if (e.code === key && !e.repeat && !isTypingTarget()) {
        e.preventDefault()
        onDown()
      }
    }

    const handleUp = (e: KeyboardEvent) => {
      if (e.code === key && !isTypingTarget()) {
        e.preventDefault()
        onUp()
      }
    }

    window.addEventListener('keydown', handleDown)
    window.addEventListener('keyup', handleUp)
    return () => {
      window.removeEventListener('keydown', handleDown)
      window.removeEventListener('keyup', handleUp)
    }
  }, [key, onDown, onUp, enabled])
}
