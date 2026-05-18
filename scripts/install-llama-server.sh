#!/usr/bin/env bash
# Build and install llama-server (llama.cpp + CUDA) on Jetson Orin / JetPack 6.x
set -euo pipefail

LLAMA_SRC="${LLAMA_SRC:-$HOME/llama.cpp}"
INSTALL_PREFIX="${INSTALL_PREFIX:-/usr/local}"
# Jetson Orin = compute capability 8.7
CUDA_ARCH="${CUDA_ARCH:-87}"
JOBS="${JOBS:-$(nproc)}"

log() { printf '\033[1;36m[llama]\033[0m %s\n' "$*"; }
err() { printf '\033[1;31m[llama]\033[0m %s\n' "$*" >&2; }

if ! command -v nvcc &>/dev/null; then
  err "nvcc not found. Install JetPack / CUDA toolkit first."
  exit 1
fi

log "Installing build dependencies..."
sudo apt-get update
sudo apt-get install -y --no-install-recommends \
  build-essential git curl \
  libcurl4-openssl-dev \
  cmake pkg-config

# Newer cmake helps on JP6 (ARM NEON / CUDA build issues)
if ! cmake --version | awk '/version/ { if ($3+0 < 3.22) exit 1 }'; then
  log "CMake looks old — installing newer cmake via pip (user)..."
  python3 -m pip install --user -U cmake 2>/dev/null || pip3 install --user -U cmake
  export PATH="$HOME/.local/bin:$PATH"
fi

if [[ ! -d "$LLAMA_SRC/.git" ]]; then
  log "Cloning llama.cpp into $LLAMA_SRC ..."
  git clone --depth 1 https://github.com/ggml-org/llama.cpp "$LLAMA_SRC"
else
  log "Updating llama.cpp in $LLAMA_SRC ..."
  git -C "$LLAMA_SRC" pull --ff-only || true
fi

cd "$LLAMA_SRC"
log "Configuring (CUDA arch ${CUDA_ARCH}, ~10–30 min build)..."
cmake -B build \
  -DGGML_CUDA=ON \
  -DCMAKE_CUDA_ARCHITECTURES="${CUDA_ARCH}" \
  -DCMAKE_BUILD_TYPE=Release \
  -DLLAMA_CURL=ON \
  -DBUILD_SHARED_LIBS=OFF

log "Building (using ${JOBS} cores)..."
cmake --build build --config Release -j"${JOBS}"

log "Installing to ${INSTALL_PREFIX} (sudo)..."
sudo cmake --install build --prefix "${INSTALL_PREFIX}"

if command -v llama-server &>/dev/null; then
  log "OK: $(command -v llama-server)"
  llama-server --version 2>/dev/null || true
  log "Done. Run: arif"
else
  err "Build finished but llama-server not on PATH."
  err "Try: export PATH=${INSTALL_PREFIX}/bin:\$PATH"
  exit 1
fi
