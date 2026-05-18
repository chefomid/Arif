import { useUiStore } from '../../stores/uiStore'
import './MicHotIndicator.css'

export function MicHotIndicator() {
  const micHot = useUiStore((s) => s.micHot)

  return (
    <div
      className={`mic-hot ${micHot ? 'active' : ''}`}
      title={micHot ? 'Microphone active (recording)' : 'Microphone off'}
      aria-live="polite"
      aria-label={micHot ? 'Microphone recording' : 'Microphone off'}
    >
      <span className="mic-dot" />
      <span className="mic-label">{micHot ? 'MIC ON' : 'mic'}</span>
    </div>
  )
}
