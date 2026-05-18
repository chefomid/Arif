#!/usr/bin/env bash
# Install JetPack CUDA toolkit on Jetson (L4T 36.2+ / JetPack 6.x)
# Run ON the Jetson: bash scripts/install-jetpack-cuda.sh
set -euo pipefail

log() { printf '\033[1;36m[jetpack]\033[0m %s\n' "$*"; }
err() { printf '\033[1;31m[jetpack]\033[0m %s\n' "$*" >&2; }

if [[ "$(uname -m)" != "aarch64" ]]; then
  err "This script must run on the Jetson (aarch64), not on Windows/Mac."
  exit 1
fi

log "Device: $(cat /proc/device-tree/model 2>/dev/null | tr -d '\0' || echo unknown)"
log "L4T: $(head -1 /etc/nv_tegra_release 2>/dev/null || echo unknown)"

if command -v nvcc &>/dev/null; then
  log "CUDA compiler already installed:"
  nvcc --version | tail -1
  read -r -p "Reinstall/upgrade JetPack CUDA packages anyway? [y/N] " ans
  [[ "${ans,,}" == "y" ]] || { log "Nothing to do."; exit 0; }
fi

if [[ ! -f /etc/apt/sources.list.d/nvidia-l4t-apt-source.list ]]; then
  err "NVIDIA apt repo not configured — flash JetPack SD image first."
  err "https://developer.nvidia.com/embedded/jetpack"
  err "Orin Nano JP6 initial setup: https://www.jetson-ai-lab.com/initial_setup_jon.html"
  exit 1
fi

log "Updating apt..."
sudo apt-get update

MODE="${1:-dev}"
case "$MODE" in
  minimal)
    log "Installing minimal CUDA build toolchain..."
    sudo apt-get install -y --no-install-recommends \
      build-essential cmake pkg-config git \
      cuda-nvcc-12-2 cuda-cudart-dev-12-2 cuda-cccl-12-2 \
      2>/dev/null || sudo apt-get install -y --no-install-recommends \
      build-essential cmake pkg-config git cuda-toolkit-12-2
    ;;
  runtime)
    log "Installing JetPack runtime (CUDA + TensorRT + cuDNN)..."
    sudo apt-get install -y nvidia-jetpack-runtime
    ;;
  dev|*)
    log "Installing full JetPack dev stack (CUDA, TensorRT, cuDNN, VPI)..."
    log "This can use several GB — ensure free space: df -h /"
    sudo apt-get install -y nvidia-jetpack
    ;;
esac

# Standard Jetson CUDA paths
if [[ -d /usr/local/cuda/bin ]]; then
  if ! grep -q '/usr/local/cuda/bin' "$HOME/.bashrc" 2>/dev/null; then
    {
      echo ''
      echo '# CUDA (JetPack)'
      echo 'export PATH=/usr/local/cuda/bin:$PATH'
      echo 'export LD_LIBRARY_PATH=/usr/local/cuda/lib64:${LD_LIBRARY_PATH:-}'
    } >>"$HOME/.bashrc"
    log "Added CUDA to ~/.bashrc — run: source ~/.bashrc"
  fi
  export PATH=/usr/local/cuda/bin:$PATH
  export LD_LIBRARY_PATH=/usr/local/cuda/lib64:${LD_LIBRARY_PATH:-}
fi

log ""
log "=== Verification ==="
if command -v nvcc &>/dev/null; then
  nvcc --version
else
  err "nvcc still not found. Try: sudo apt install cuda-toolkit-12-2"
  exit 1
fi

if command -v tegrastats &>/dev/null; then
  log "GPU: tegrastats available (Jetson OK)"
else
  log "Note: tegrastats not found (unusual on Jetson)"
fi

log ""
log "Next: bash scripts/install-llama-server.sh"
log "Then: arif"
