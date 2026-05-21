#!/usr/bin/env bash
# Free GPU/RAM on Jetson for Nemotron: max clocks + safely stop non-essential apps.
# Called automatically by `arif` when ARIF_ENGAGE_GPU=true (default on Jetson).
set -euo pipefail

log() { printf '\033[1;35m[gpu-prep]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[gpu-prep]\033[0m %s\n' "$*"; }

is_jetson() {
  [[ "$(uname -m)" == "aarch64" ]] && {
    [[ -f /etc/nv_tegra_release ]] || grep -qi nvidia /proc/device-tree/model 2>/dev/null
  }
}

# Never stop these (substring match on cmdline).
is_protected() {
  local cmd="$1"
  [[ "$cmd" =~ gnome-shell|Xorg|Xwayland|gdm|sshd|systemd|pipewire|pulseaudio|wireplumber|NetworkManager|dbus-daemon|dbus-broker|nvpmodel|jetson_clocks|llama-server|uvicorn|run\.py|scripts/arif|backend/run\.py|jetson-gpu-prep|openssh|login|bash.*arif|python.*run\.py ]]
}

stop_process_name() {
  local name=$1
  local pid cmdline
  while read -r pid; do
    [[ -z "$pid" ]] && continue
    [[ "$pid" == "$$" ]] && continue
    cmdline="$(ps -o args= -p "$pid" 2>/dev/null || true)"
    [[ -z "$cmdline" ]] && continue
    is_protected "$cmdline" && continue
    log "SIGTERM $name (pid $pid)"
    kill -TERM "$pid" 2>/dev/null || true
  done < <(pgrep -x "$name" 2>/dev/null || true)
}

stop_pattern() {
  local pattern=$1
  local pid cmdline
  while read -r pid cmdline; do
    [[ -z "$pid" ]] && continue
    [[ "$pid" == "$$" ]] && continue
    is_protected "$cmdline" && continue
    log "SIGTERM pid $pid (${cmdline:0:72})"
    kill -TERM "$pid" 2>/dev/null || true
  done < <(pgrep -af "$pattern" 2>/dev/null || true)
}

if ! is_jetson; then
  log "Not a Jetson (aarch64 + NVIDIA) — skipping."
  exit 0
fi

log "Jetson: $(tr -d '\0' </proc/device-tree/model 2>/dev/null || echo unknown)"

ARIF_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ -f "$ARIF_ROOT/scripts/jetson-swap.sh" ]]; then
  bash "$ARIF_ROOT/scripts/jetson-swap.sh" || true
fi

if command -v nvpmodel &>/dev/null; then
  log "Setting max performance (nvpmodel)..."
  sudo nvpmodel -m 0 2>/dev/null || sudo nvpmodel -m 2 2>/dev/null || warn "nvpmodel failed (sudo?)"
fi

if command -v jetson_clocks &>/dev/null; then
  log "Locking clocks (jetson_clocks)..."
  sudo jetson_clocks 2>/dev/null || warn "jetson_clocks failed (sudo?)"
fi

# killall is narrow and safer than broad pkill -f
for exe in chromium-browser chromium chrome firefox; do
  if command -v killall &>/dev/null && killall -0 "$exe" 2>/dev/null; then
    log "Stopping $exe..."
    killall -TERM "$exe" 2>/dev/null || true
  fi
done

# Optional desktop apps that often reserve GPU/RAM
for exe in libreoffice soffice; do
  if command -v killall &>/dev/null && killall -0 "$exe" 2>/dev/null; then
    log "Stopping $exe..."
    killall -TERM "$exe" 2>/dev/null || true
  fi
done

# Extra llama-server instances (not ours — arif hasn't started yet)
stop_pattern "llama-server"

# VS Code / Cursor (optional dev IDEs)
stop_process_name code
stop_pattern "/usr/share/cursor/cursor"

sleep 1

for exe in chromium-browser chromium chrome firefox; do
  killall -KILL "$exe" 2>/dev/null || true
done

sync
if [[ -r /proc/sys/vm/drop_caches ]]; then
  log "Dropping page cache..."
  echo 3 | sudo tee /proc/sys/vm/drop_caches >/dev/null 2>&1 || warn "drop_caches skipped (sudo?)"
fi

log "Memory after prep:"
free -h | while read -r line; do log "  $line"; done

if command -v tegrastats &>/dev/null; then
  timeout 3 tegrastats --interval 400 2>/dev/null | head -1 | while read -r line; do
    log "  $line"
  done || true
fi

log "Done. Nemotron can use GPU (LLM_GPU_LAYERS=999)."
