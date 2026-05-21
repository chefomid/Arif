#!/usr/bin/env bash
# Ensure extra swap on 8GB Jetson (helps llama.cpp unified-memory pressure).
set -euo pipefail

SWAP_GB="${ARIF_SWAP_GB:-8}"
SWAP_FILE="${ARIF_SWAP_FILE:-/swapfile_arif}"

log() { printf '\033[1;35m[swap]\033[0m %s\n' "$*"; }

is_jetson() {
  [[ "$(uname -m)" == "aarch64" ]] && {
    [[ -f /etc/nv_tegra_release ]] || grep -qi nvidia /proc/device-tree/model 2>/dev/null
  }
}

if ! is_jetson; then
  exit 0
fi

total_swap_kb="$(awk '/SwapTotal:/ {print $2}' /proc/meminfo)"
need_kb=$((SWAP_GB * 1024 * 1024))

if [[ "$total_swap_kb" -ge "$need_kb" ]]; then
  log "Swap OK ($(awk "BEGIN {printf \"%.1f\", $total_swap_kb/1024/1024}") GB)"
  exit 0
fi

if [[ -f "$SWAP_FILE" ]] && swapon --show 2>/dev/null | grep -qF "$SWAP_FILE"; then
  log "Swap file already active: $SWAP_FILE"
  exit 0
fi

log "Adding ${SWAP_GB}GB swap at $SWAP_FILE (one-time, needs sudo)..."
if [[ ! -f "$SWAP_FILE" ]]; then
  sudo fallocate -l "${SWAP_GB}G" "$SWAP_FILE" 2>/dev/null \
    || sudo dd if=/dev/zero of="$SWAP_FILE" bs=1M count=$((SWAP_GB * 1024)) status=progress
  sudo chmod 600 "$SWAP_FILE"
  sudo mkswap "$SWAP_FILE"
fi
sudo swapon "$SWAP_FILE" 2>/dev/null || log "Could not enable swap (already on?)"
swapon --show 2>/dev/null || true
