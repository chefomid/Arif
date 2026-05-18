#!/usr/bin/env bash
# Download models for Arif on Jetson (run on device with network)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "==> Downloading Nemotron3 Nano 4B GGUF (Q4_K_M)..."
if [ ! -f "NVIDIA-Nemotron3-Nano-4B-Q4_K_M.gguf" ]; then
  pip install -q huggingface_hub 2>/dev/null || true
  python3 - <<'PY'
from huggingface_hub import hf_hub_download
path = hf_hub_download(
    repo_id="nvidia/NVIDIA-Nemotron-3-Nano-4B-GGUF",
    filename="NVIDIA-Nemotron3-Nano-4B-Q4_K_M.gguf",
    local_dir=".",
)
print(f"Downloaded: {path}")
PY
fi

echo "==> Downloading YOLO11n (PyTorch) for TensorRT export..."
python3 - <<'PY'
from ultralytics import YOLO
YOLO("yolo11n.pt")
print("yolo11n.pt ready")
PY

echo "==> Export YOLO11n to TensorRT engine (Jetson GPU)..."
yolo export model=yolo11n.pt format=engine device=0 2>/dev/null || \
  echo "WARN: TensorRT export failed – will use .pt fallback at runtime"

if [ -f "yolo11n.engine" ]; then
  echo "TensorRT engine: models/yolo11n.engine"
else
  echo "Using PyTorch weights; copy yolo11n.pt to models/ if needed"
fi

echo "==> Whisper models download on first STT run (faster-whisper)."
echo "Done. Start llama-server with the Nemotron GGUF, then run the backend."
