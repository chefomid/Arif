#!/usr/bin/env bash
# Setup Arif on Jetson Orin Nano Super (JetPack 6.x)
set -euo pipefail

ARIF_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ARIF_ROOT"

echo "==> CUDA / JetPack (if nvcc missing)"
if ! command -v nvcc &>/dev/null; then
  read -r -p "Install JetPack CUDA via apt? [Y/n] " cuda_ans
  if [[ "${cuda_ans,,}" != "n" ]]; then
    bash "$ARIF_ROOT/scripts/install-jetpack-cuda.sh" minimal || \
      bash "$ARIF_ROOT/scripts/install-jetpack-cuda.sh" dev || true
  fi
fi

echo "==> System packages"
sudo apt-get update
sudo apt-get install -y \
  python3-pip python3-venv \
  portaudio19-dev libsndfile1 \
  v4l-utils \
  build-essential

echo "==> Python virtualenv (requires Python 3.11+)"
if ! python3 -c 'import sys; exit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; then
  echo "ERROR: Python 3.11+ required. Install with: sudo apt install python3.11 python3.11-venv"
  exit 1
fi
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r backend/requirements.txt

echo "==> Environment file"
if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env from .env.example – edit as needed"
fi

echo "==> Download models (optional, may take a while)"
read -r -p "Download Nemotron + YOLO now? [y/N] " ans
if [[ "${ans,,}" == "y" ]]; then
  bash models/download_models.sh
fi

echo "==> llama.cpp / llama-server"
if ! command -v llama-server &>/dev/null; then
  read -r -p "Build llama-server now? (~15-30 min) [y/N] " llama_ans
  if [[ "${llama_ans,,}" == "y" ]]; then
    bash "$ARIF_ROOT/scripts/install-llama-server.sh"
  else
    echo "Install later: bash scripts/install-llama-server.sh"
    echo "Guide: https://www.jetson-ai-lab.com/models/nemotron3-nano-4b/"
  fi
fi

echo "==> Performance mode"
if command -v nvpmodel &>/dev/null; then
  sudo nvpmodel -m 0 2>/dev/null || true
  sudo jetson_clocks 2>/dev/null || true
fi

bash "$ARIF_ROOT/scripts/install-arif.sh" || true

echo ""
echo "Setup complete."
echo "  Start everything:  arif"
echo "  Stop:              arif stop"
echo "  Open UI:           http://<jetson-ip>:8000"
echo ""
echo "Optional systemd units in deploy/systemd/ (edit paths/user first)."
