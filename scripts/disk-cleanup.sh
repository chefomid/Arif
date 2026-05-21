#!/usr/bin/env bash
# Free disk space on Jetson / Linux (safe defaults). Run when git/df says "No space left".
# Usage: bash scripts/disk-cleanup.sh [--aggressive]
set -euo pipefail

AGGRESSIVE=0
[[ "${1:-}" == "--aggressive" ]] && AGGRESSIVE=1

log() { printf '\033[1;33m[cleanup]\033[0m %s\n' "$*"; }

log "Disk before:"
df -h / | tail -1

log "Clearing apt cache..."
sudo apt-get clean 2>/dev/null || true
sudo apt-get autoremove -y 2>/dev/null || true

log "Truncating old journals (keep 100MB)..."
sudo journalctl --vacuum-size=100M 2>/dev/null || true

log "Removing temp files..."
rm -rf /tmp/arif-llama.*.log 2>/dev/null || true
rm -rf /tmp/pip-* 2>/dev/null || true
find /tmp -maxdepth 1 -type f -mtime +3 -delete 2>/dev/null || true

log "Clearing pip cache..."
python3 -m pip cache purge 2>/dev/null || pip3 cache purge 2>/dev/null || true
rm -rf "$HOME/.cache/pip" 2>/dev/null || true

log "Clearing Python __pycache__ under ~/Desktop..."
find "$HOME/Desktop" -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true

if [[ "$AGGRESSIVE" -eq 1 ]]; then
  log "Aggressive: Hugging Face hub cache (re-download models if needed)..."
  rm -rf "$HOME/.cache/huggingface/hub" 2>/dev/null || true
  log "Aggressive: Ultralytics / torch caches..."
  rm -rf "$HOME/.cache/ultralytics" 2>/dev/null || true
  rm -rf "$HOME/.cache/torch" 2>/dev/null || true
fi

log "Disk after:"
df -h / | tail -1
log "Largest dirs in home (top 15):"
du -sh "$HOME"/* "$HOME"/.[!.]* 2>/dev/null | sort -hr | head -15 || true

log "Done. If still full: remove duplicate Arif clones or move models off disk."
log "  du -sh ~/Desktop/* ~/llama.cpp ~/Arif*"
