import { useCallback, useRef } from 'react'
import { wsClient } from '../lib/wsClient'
import { useUiStore } from '../stores/uiStore'

export function usePushToTalk() {
  const holding = useRef(false)
  const setMicHot = useUiStore((s) => s.setMicHot)

  const start = useCallback(() => {
    if (holding.current) return
    holding.current = true
    setMicHot(true)
    wsClient.send('ptt_start')
  }, [setMicHot])

  const end = useCallback(() => {
    if (!holding.current) return
    holding.current = false
    setMicHot(false)
    wsClient.send('ptt_end')
  }, [setMicHot])

  return { start, end }
}
