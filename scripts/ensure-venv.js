const fs = require('fs')
const path = require('path')

const root = path.join(__dirname, '..')
const isWin = process.platform === 'win32'
const python = path.join(root, '.venv', isWin ? 'Scripts' : 'bin', isWin ? 'python.exe' : 'python')

if (!fs.existsSync(python)) {
  console.warn('\n[arif] No .venv found. Run: npm run setup\n')
}
