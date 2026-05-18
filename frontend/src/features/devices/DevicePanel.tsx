import { useEffect, useRef, useState } from 'react'
import { useDeviceStore } from '../../stores/deviceStore'
import { useUiStore } from '../../stores/uiStore'
import './DevicePanel.css'

type Row =
  | { kind: 'mic-default' }
  | { kind: 'mic'; index: number }
  | { kind: 'cam'; index: number }

export function DevicePanel() {
  const goToChat = useUiStore((s) => s.goToChat)
  const fetchDevices = useDeviceStore((s) => s.fetchDevices)
  const autoSelect = useDeviceStore((s) => s.autoSelect)
  const selectMic = useDeviceStore((s) => s.selectMic)
  const selectCamera = useDeviceStore((s) => s.selectCamera)
  const audioDevices = useDeviceStore((s) => s.audioDevices)
  const cameraDevices = useDeviceStore((s) => s.cameraDevices)
  const micName = useDeviceStore((s) => s.micName)
  const cameraName = useDeviceStore((s) => s.cameraName)
  const loading = useDeviceStore((s) => s.loading)
  const error = useDeviceStore((s) => s.error)

  const [cursor, setCursor] = useState(0)
  const panelRef = useRef<HTMLDivElement>(null)

  const rows: Row[] = [
    { kind: 'mic-default' },
    ...audioDevices.map((d) => ({ kind: 'mic' as const, index: d.index })),
    ...cameraDevices.map((d) => ({ kind: 'cam' as const, index: d.index })),
  ]

  useEffect(() => {
    fetchDevices()
    panelRef.current?.focus()
  }, [fetchDevices])

  useEffect(() => {
    setCursor((c) => Math.min(c, Math.max(0, rows.length - 1)))
  }, [rows.length])

  useEffect(() => {
    const onKeyDown = async (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault()
        goToChat()
        return
      }

      if (e.key === 'a' || e.key === 'A') {
        e.preventDefault()
        await autoSelect()
        return
      }

      if (e.key === 'ArrowDown') {
        e.preventDefault()
        setCursor((c) => Math.min(c + 1, rows.length - 1))
        return
      }

      if (e.key === 'ArrowUp') {
        e.preventDefault()
        setCursor((c) => Math.max(c - 1, 0))
        return
      }

      if (e.key === 'Enter' && rows.length > 0) {
        e.preventDefault()
        const row = rows[cursor]
        try {
          if (row.kind === 'mic-default') {
            await selectMic(null)
          } else if (row.kind === 'mic') {
            await selectMic(row.index)
          } else if (row.kind === 'cam') {
            await selectCamera(row.index)
          }
        } catch {
          /* ignore */
        }
      }
    }

    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [cursor, rows, goToChat, autoSelect, selectMic, selectCamera])

  const labelFor = (row: Row) => {
    if (row.kind === 'mic-default') {
      return '[System default microphone]'
    }
    if (row.kind === 'mic') {
      const d = audioDevices.find((x) => x.index === row.index)
      return d ? `Mic: ${d.name}` : `Mic ${row.index}`
    }
    const d = cameraDevices.find((x) => x.index === row.index)
    return d ? `Cam: ${d.name}` : `Camera ${row.index}`
  }

  const isSelected = (row: Row) => {
    if (row.kind === 'mic-default') {
      return !audioDevices.some((d) => d.selected)
    }
    if (row.kind === 'mic') {
      return audioDevices.find((d) => d.index === row.index)?.selected
    }
    return cameraDevices.find((d) => d.index === row.index)?.selected
  }

  return (
    <div
      className="device-panel"
      ref={panelRef}
      tabIndex={-1}
      role="dialog"
      aria-label="Device selection"
    >
      <div className="device-header">
        <h2># Devices</h2>
        <span className="device-hint">↑↓ move · Enter select · A auto · Esc back</span>
      </div>

      <div className="device-current">
        <p>
          <span className="label">Mic:</span> {micName}
        </p>
        <p>
          <span className="label">Cam:</span> {cameraName}
        </p>
      </div>

      {loading && <p className="device-status">Scanning devices…</p>}
      {error && <p className="device-error">{error}</p>}

      <ul className="device-list" role="listbox">
        {rows.length === 0 && !loading && (
          <li className="device-empty">No devices found. Plug in USB mic/camera and press A.</li>
        )}
        {rows.map((row, i) => (
          <li
            key={`${row.kind}-${row.kind === 'mic-default' ? 'd' : row.index}`}
            className={`device-row ${i === cursor ? 'focused' : ''} ${isSelected(row) ? 'selected' : ''}`}
            role="option"
            aria-selected={i === cursor}
          >
            {labelFor(row)}
            {isSelected(row) && <span className="sel-tag"> ◀ active</span>}
          </li>
        ))}
      </ul>
    </div>
  )
}
