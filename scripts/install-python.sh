#!/usr/bin/env bash
# Install Python 3.11+ on Linux (Jetson / Ubuntu / Debian) and set up Arif .venv.
# Run ON the device after git pull:
#   bash scripts/install-python.sh
set -euo pipefail

ARIF_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ARIF_ROOT"

log() { printf '\033[1;36m[python]\033[0m %s\n' "$*"; }
err() { printf '\033[1;31m[python]\033[0m %s\n' "$*" >&2; }

RUN_SETUP=1
for arg in "$@"; do
  case "$arg" in
    --no-setup) RUN_SETUP=0 ;;
    -h | --help)
      echo "Usage: bash scripts/install-python.sh [--no-setup]"
      echo "  Installs Python 3.11+ via apt, then runs scripts/setup.py (unless --no-setup)."
      exit 0
      ;;
  esac
done

if [[ "$(uname -s)" != "Linux" ]]; then
  err "This script is for Linux (Jetson / Ubuntu). On Windows use python.org or winget."
  exit 1
fi

python_ok() {
  local cmd=$1
  command -v "$cmd" &>/dev/null \
    && "$cmd" -c 'import sys; exit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null
}

pick_python() {
  local cmd
  for cmd in python3.13 python3.12 python3.11 python3; do
    if python_ok "$cmd"; then
      echo "$cmd"
      return 0
    fi
  done
  return 1
}

install_via_apt() {
  local ver=$1
  log "Installing Python ${ver} from apt..."
  sudo apt-get update
  sudo apt-get install -y \
    "python${ver}" \
    "python${ver}-venv" \
    "python${ver}-dev" \
    python3-pip \
    build-essential
}

log "Host: $(uname -m) — $(. /etc/os-release 2>/dev/null && echo "$PRETTY_NAME" || echo Linux)"

PYTHON=""
if PYTHON="$(pick_python)"; then
  log "Found: $($PYTHON --version)"
else
  log "Python 3.11+ not found — installing via apt..."
  INSTALLED=0
  for ver in 3.12 3.11; do
    if install_via_apt "$ver"; then
      INSTALLED=1
      break
    fi
  done
  if [[ "$INSTALLED" -eq 0 ]]; then
    err "Could not install python3.12 or python3.11 from apt."
    err "On Jetson: use JetPack 6.x (Ubuntu 22.04) and run: sudo apt update"
    err "Manual: sudo apt install python3.11 python3.11-venv python3.11-dev"
    exit 1
  fi
  PYTHON="$(pick_python)" || true
fi

if [[ -z "$PYTHON" ]]; then
  err "Python 3.11+ still not available after install."
  exit 1
fi

log "Using: $($PYTHON --version)"

if [[ -d "$ARIF_ROOT/.venv" ]]; then
  if ! "$ARIF_ROOT/.venv/bin/python" -c 'import sys; exit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; then
    log "Removing old .venv (Python < 3.11)..."
    rm -rf "$ARIF_ROOT/.venv"
  fi
fi

if [[ "$RUN_SETUP" -eq 1 ]]; then
  log "Running scripts/setup.py..."
  "$PYTHON" "$ARIF_ROOT/scripts/setup.py"
fi

echo ""
log "Done."
echo "  Start Arif:  arif"
echo "  Or manual:   source .venv/bin/activate && python backend/run.py"
echo "  UI:          http://$(hostname -I 2>/dev/null | awk '{print $1}' || echo localhost):8000"
