#!/usr/bin/env bash
# Setup Arif on Jetson Orin Nano Super (JetPack 6.x)
set -euo pipefail

ARIF_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ARIF_ROOT"

echo "==> System packages"
sudo apt-get update
sudo apt-get install -y \
  python3-pip python3-venv \
  portaudio19-dev libsndfile1 \
  v4l-utils \
  build-essential

echo "==> Python virtualenv"
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r backend/requirements.txt

echo "==> Frontend build"
if command -v npm &>/dev/null; then
  cd frontend
  npm install
  npm run build
  cd "$ARIF_ROOT"
else
  echo "WARN: npm not found – build frontend on dev machine and copy frontend/dist"
fi

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
  echo "Install llama.cpp with CUDA for Jetson:"
  echo "  https://www.jetson-ai-lab.com/models/nemotron3-nano-4b/"
fi

echo "==> Performance mode"
if command -v nvpmodel &>/dev/null; then
  sudo nvpmodel -m 0 2>/dev/null || true
  sudo jetson_clocks 2>/dev/null || true
fi

echo ""
echo "Setup complete."
echo "  1. Start Nemotron:  llama-server -m models/NVIDIA-Nemotron3-Nano-4B-Q4_K_M.gguf --host 0.0.0.0 --port 8080 --n-gpu-layers 999 --alias nemotron"
echo "  2. Start backend:   cd backend && ../.venv/bin/python run.py"
echo "  3. Open UI:         http://<jetson-ip>:8000  (or npm run dev in frontend/)"
echo ""
echo "Optional systemd units in deploy/systemd/ (edit paths/user first)."
