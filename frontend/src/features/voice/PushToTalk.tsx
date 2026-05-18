import { usePushToTalk } from '../../hooks/usePushToTalk'
import { useKeyboardHold } from '../../hooks/useKeyboard'
import { useUiStore } from '../../stores/uiStore'
import './PushToTalk.css'

export function PushToTalk() {
  const { start, end } = usePushToTalk()
  const micHot = useUiStore((s) => s.micHot)

  useKeyboardHold('Space', start, end)

  return (
    <button
      type="button"
      className={`ptt-button ${micHot ? 'hot' : ''}`}
      onMouseDown={start}
      onMouseUp={end}
      onMouseLeave={end}
      onTouchStart={(e) => {
        e.preventDefault()
        start()
      }}
      onTouchEnd={(e) => {
        e.preventDefault()
        end()
      }}
      title="Hold to talk — or hold Space (when not typing)"
    >
      <span className="ptt-icon">{micHot ? '●' : '○'}</span>
      <span className="ptt-label">{micHot ? '[PTT ACTIVE]' : '[Hold Space]'}</span>
    </button>
  )
}
