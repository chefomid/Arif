import { useEffect, useRef } from 'react'
import { useUiStore } from '../../stores/uiStore'
import './HelpPanel.css'

const SHORTCUTS = [
  ['/', 'Focus message input'],
  ['Space (hold)', 'Push-to-talk / record voice'],
  ['Enter', 'Send message (in input)'],
  ['C', 'Toggle camera view'],
  ['D', 'Open device picker'],
  ['A', 'Auto-detect devices (in device picker)'],
  ['↑ / ↓', 'Navigate device list'],
  ['Esc', 'Back to chat / close panel'],
  ['?', 'This help screen'],
]

export function HelpPanel() {
  const goToChat = useUiStore((s) => s.goToChat)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    ref.current?.focus()
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' || e.key === '?') {
        e.preventDefault()
        goToChat()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [goToChat])

  return (
    <div className="help-panel" ref={ref} tabIndex={-1} role="dialog" aria-label="Keyboard help">
      <h2># Keyboard shortcuts</h2>
      <p className="help-note">Navigation works without mouse. Esc returns to chat.</p>
      <table className="help-table">
        <tbody>
          {SHORTCUTS.map(([key, desc]) => (
            <tr key={key}>
              <td className="help-key">{key}</td>
              <td className="help-desc">{desc}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="help-footer">Press Esc or ? to close</p>
    </div>
  )
}
