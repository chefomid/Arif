#!/usr/bin/env bash
# After git pull on Jetson: free disk, fix .env, ensure venv. One command.
set -euo pipefail

ARIF_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ARIF_ROOT"

log() { printf '\033[1;36m[update]\033[0m %s\n' "$*"; }
err() { printf '\033[1;31m[update]\033[0m %s\n' "$*" >&2; }

log "Repo: $ARIF_ROOT"
log "Disk before:"
df -h / | tail -1

if command -v git &>/dev/null && [[ -d .git ]]; then
  log "git pull..."
  git pull
else
  err "Not a git repo — skip pull or clone first"
fi

if [[ -f scripts/disk-cleanup.sh ]]; then
  bash scripts/disk-cleanup.sh || true
fi

bash scripts/configure-env.sh

if [[ ! -d .venv/bin ]] || ! .venv/bin/python -c 'import sys; exit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; then
  log "Python venv missing or old — running install-python.sh..."
  bash scripts/install-python.sh
fi

if [[ ! -f models/NVIDIA-Nemotron3-Nano-4B-Q4_K_M.gguf ]]; then
  log "Nemotron GGUF missing — run: bash models/download_models.sh"
fi

if ! command -v llama-server &>/dev/null; then
  log "llama-server not found — run: bash scripts/install-llama-server.sh"
fi

bash scripts/install-arif.sh 2>/dev/null || true

log "Disk after:"
df -h / | tail -1
log ""
log "Start Arif (CPU Nemotron, wait 3–6 min on first load):"
log "  arif stop"
log "  arif"
