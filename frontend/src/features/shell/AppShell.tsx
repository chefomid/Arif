import { useEffect } from 'react'
import { CameraView } from '../camera/CameraView'
import { ChatPanel } from '../chat/ChatPanel'
import { DevicePanel } from '../devices/DevicePanel'
import { MicHotIndicator } from '../voice/MicHotIndicator'
import { PushToTalk } from '../voice/PushToTalk'
import { useDeviceStore } from '../../stores/deviceStore'
import { useGlobalKeyboard } from '../../hooks/useGlobalKeyboard'
import { useUiStore } from '../../stores/uiStore'
import { HelpPanel } from './HelpPanel'
import './AppShell.css'

export function AppShell() {
  const view = useUiStore((s) => s.view)
  const toggleCamera = useUiStore((s) => s.toggleCamera)
  const openDevices = useUiStore((s) => s.openDevices)
  const openHelp = useUiStore((s) => s.openHelp)
  const wsConnected = useUiStore((s) => s.wsConnected)
  const llmHealthy = useUiStore((s) => s.llmHealthy)
  const setLlmHealthy = useUiStore((s) => s.setLlmHealthy)
  const micName = useDeviceStore((s) => s.micName)
  const cameraName = useDeviceStore((s) => s.cameraName)
  const fetchDevices = useDeviceStore((s) => s.fetchDevices)

  useGlobalKeyboard()

  useEffect(() => {
    fetchDevices()
  }, [fetchDevices])

  useEffect(() => {
    const check = async () => {
      try {
        const res = await fetch('/health')
        const data = await res.json()
        setLlmHealthy(data.llm === true)
      } catch {
        setLlmHealthy(false)
      }
    }
    check()
    const id = setInterval(check, 10000)
    return () => clearInterval(id)
  }, [setLlmHealthy])

  return (
    <div className="app-shell">
      <header className="toolbar">
        <div className="toolbar-brand">
          <span className="ps-prompt">PS</span>
          <h1>Arif://multimodal</h1>
        </div>
        <div className="toolbar-actions">
          <MicHotIndicator />
          <PushToTalk />
          <button
            type="button"
            className={`toolbar-btn ${view === 'devices' ? 'active' : ''}`}
            onClick={openDevices}
            title="Devices (D)"
          >
            [Devices]
          </button>
          <button
            type="button"
            className={`toolbar-btn cam-toggle ${view === 'camera' ? 'active' : ''}`}
            onClick={toggleCamera}
            title="Camera (C)"
          >
            [Camera]
          </button>
          <button
            type="button"
            className={`toolbar-btn ${view === 'help' ? 'active' : ''}`}
            onClick={openHelp}
            title="Help (?)"
          >
            [?]
          </button>
        </div>
        <div className="status" title="Connection status">
          <span className="status-item">
            <span className={`dot ws ${wsConnected ? 'on' : 'off'}`} />
            <span className="status-label">link</span>
          </span>
          <span className="status-item">
            <span className={`dot llm ${llmHealthy ? 'on' : 'off'}`} />
            <span className="status-label">llm</span>
          </span>
        </div>
      </header>

      <div className="device-bar">
        <span className="device-bar-item">mic: {micName}</span>
        <span className="device-bar-sep">|</span>
        <span className="device-bar-item">cam: {cameraName}</span>
        <span className="device-bar-hint">? help · D devices · C camera · Esc back</span>
      </div>

      <main className={`main view-${view}`}>
        {view === 'chat' && (
          <section className="panel chat-section">
            <ChatPanel />
          </section>
        )}
        {view === 'camera' && (
          <section className="panel camera-section">
            <CameraView />
          </section>
        )}
        {view === 'devices' && (
          <section className="panel devices-section">
            <DevicePanel />
          </section>
        )}
        {view === 'help' && (
          <section className="panel help-section">
            <HelpPanel />
          </section>
        )}
      </main>
    </div>
  )
}
