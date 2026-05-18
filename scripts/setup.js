const { spawnSync } = require('child_process')
const fs = require('fs')
const path = require('path')

const root = path.join(__dirname, '..')
const isWin = process.platform === 'win32'
const venvPython = path.join(root, '.venv', isWin ? 'Scripts' : 'bin', isWin ? 'python.exe' : 'python')
const venvPip = path.join(root, '.venv', isWin ? 'Scripts' : 'bin', isWin ? 'pip.exe' : 'pip')

function run(cmd, args, opts = {}) {
  const r = spawnSync(cmd, args, { stdio: 'inherit', cwd: opts.cwd || root, shell: isWin })
  if (r.status !== 0) process.exit(r.status ?? 1)
}

console.log('==> Creating Python virtualenv...')
if (!fs.existsSync(venvPython)) {
  run('python', ['-m', 'venv', '.venv'])
}

console.log('==> Installing backend dependencies...')
run(venvPip, ['install', '-r', 'backend/requirements.txt'])

console.log('==> Installing frontend dependencies...')
run('npm', ['install'], { cwd: path.join(root, 'frontend') })

if (!fs.existsSync(path.join(root, '.env'))) {
  fs.copyFileSync(path.join(root, '.env.example'), path.join(root, '.env'))
  console.log('==> Created .env from .env.example')
}

console.log('\nSetup complete. Run: npm run dev:all')
