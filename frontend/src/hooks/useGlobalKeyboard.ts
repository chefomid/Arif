import { useEffect } from 'react'
import { useUiStore } from '../stores/uiStore'

function isTypingTarget(): boolean {
  const el = document.activeElement
  if (!el) return false
  const tag = el.tagName
  return (
    tag === 'INPUT' ||
    tag === 'TEXTAREA' ||
    (el instanceof HTMLElement && el.isContentEditable)
  )
}

export function useGlobalKeyboard() {
  const view = useUiStore((s) => s.view)
  const toggleCamera = useUiStore((s) => s.toggleCamera)
  const openDevices = useUiStore((s) => s.openDevices)
  const openHelp = useUiStore((s) => s.openHelp)
  const goToChat = useUiStore((s) => s.goToChat)

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        if (view !== 'chat') {
          e.preventDefault()
          goToChat()
        }
        return
      }

      if (view === 'devices' || view === 'help') {
        return
      }

      if (isTypingTarget()) {
        return
      }

      switch (e.key) {
        case '?':
          e.preventDefault()
          openHelp()
          break
        case 'd':
        case 'D':
          e.preventDefault()
          openDevices()
          break
        case 'c':
        case 'C':
          e.preventDefault()
          toggleCamera()
          break
        case '/':
          e.preventDefault()
          document.getElementById('chat-input')?.focus()
          break
        default:
          break
      }
    }

    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [view, toggleCamera, openDevices, openHelp, goToChat])
}
