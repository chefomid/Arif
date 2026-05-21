#!/usr/bin/env bash
# Write/fix .env for Jetson (CPU-only LLM, sane camera/YOLO defaults).
set -euo pipefail

ARIF_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ARIF_ROOT"
QUIET=0
[[ "${1:-}" == "--quiet" ]] && QUIET=1

log() { [[ "$QUIET" -eq 1 ]] || printf '\033[1;32m[configure]\033[0m %s\n' "$*"; }

mkdir -p "$ARIF_ROOT/logs"

if [[ ! -f "$ARIF_ROOT/.env.example" ]]; then
  echo "ERROR: .env.example missing in $ARIF_ROOT" >&2
  exit 1
fi

if [[ ! -f "$ARIF_ROOT/.env" ]]; then
  cp "$ARIF_ROOT/.env.example" "$ARIF_ROOT/.env"
  log "Created .env from .env.example"
fi

set_kv() {
  local key=$1 val=$2
  if grep -q "^${key}=" "$ARIF_ROOT/.env" 2>/dev/null; then
    sed -i "s|^${key}=.*|${key}=${val}|" "$ARIF_ROOT/.env"
  else
    echo "${key}=${val}" >>"$ARIF_ROOT/.env"
  fi
}

# CPU-only Nemotron (stable on 8GB Orin Nano)
set_kv ARIF_ENGAGE_GPU false
set_kv ARIF_LLM_AUTO_FIT false
set_kv LLM_GPU_LAYERS 0
set_kv LLM_CTX_SIZE 2048
set_kv LLM_BASE_URL "http://127.0.0.1:8080/v1"
set_kv LLM_MODEL nemotron
set_kv LLM_API_KEY not-needed

# Backend / sensors
set_kv ARIF_HOST 0.0.0.0
set_kv ARIF_PORT 8000
set_kv WHISPER_MODEL tiny.en
set_kv WHISPER_DEVICE cpu
set_kv WHISPER_COMPUTE_TYPE int8
set_kv CAMERA_DEVICE 0
set_kv YOLO_FPS_CAP 4
set_kv YOLO_FPS_MIN 2

if [[ -f "$ARIF_ROOT/models/yolo11n.engine" ]]; then
  set_kv YOLO_MODEL models/yolo11n.engine
elif [[ -f "$ARIF_ROOT/models/yolo11n.pt" ]]; then
  set_kv YOLO_MODEL models/yolo11n.pt
else
  set_kv YOLO_MODEL models/yolo11n.pt
fi

chmod +x "$ARIF_ROOT/arif" 2>/dev/null || true
chmod +x "$ARIF_ROOT/scripts/"*.sh 2>/dev/null || true

log "Configured .env (CPU LLM, CAMERA_DEVICE=0)"
log "  LLM_GPU_LAYERS=0  LLM_CTX_SIZE=2048  ARIF_ENGAGE_GPU=false"
