const { spawn } = require('child_process')
const fs = require('fs')
const path = require('path')

const root = path.join(__dirname, '..')
const isWin = process.platform === 'win32'
const python = path.join(root, '.venv', isWin ? 'Scripts' : 'bin', isWin ? 'python.exe' : 'python')
const backendDir = path.join(root, 'backend')

if (!fs.existsSync(python)) {
  console.error('[backend] Virtualenv not found. Run: npm run setup')
  process.exit(1)
}

if (!fs.existsSync(path.join(root, '.env'))) {
  fs.copyFileSync(path.join(root, '.env.example'), path.join(root, '.env'))
  console.log('[backend] Created .env from .env.example')
}

const child = spawn(python, ['run.py'], {
  cwd: backendDir,
  stdio: 'inherit',
  env: { ...process.env },
})

child.on('exit', (code, signal) => {
  if (signal) process.kill(process.pid, signal)
  process.exit(code ?? 0)
})

child.on('error', (err) => {
  console.error('[backend] Failed to start:', err.message)
  process.exit(1)
})
