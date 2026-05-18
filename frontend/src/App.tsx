import { AppShell } from './features/shell/AppShell'
import { useWebSocket } from './hooks/useWebSocket'
import './App.css'

function App() {
  useWebSocket()
  return <AppShell />
}

export default App
