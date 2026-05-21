#!/usr/bin/env bash
# Download models for Arif on Jetson (run on device with network)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
ARIF_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

NEMOTRON="NVIDIA-Nemotron3-Nano-4B-Q4_K_M.gguf"

pick_python() {
  if [[ -x "$ARIF_ROOT/.venv/bin/python" ]]; then
    echo "$ARIF_ROOT/.venv/bin/python"
  elif command -v python3.11 &>/dev/null; then
    echo python3.11
  else
    echo python3
  fi
}

PY="$(pick_python)"
echo "==> Using: $($PY --version)"

echo "==> Downloading Nemotron3 Nano 4B GGUF (Q4_K_M)..."
if [[ ! -f "$NEMOTRON" ]]; then
  "$PY" -m pip install -q huggingface_hub
  "$PY" - <<'PY'
from huggingface_hub import hf_hub_download
path = hf_hub_download(
    repo_id="nvidia/NVIDIA-Nemotron-3-Nano-4B-GGUF",
    filename="NVIDIA-Nemotron3-Nano-4B-Q4_K_M.gguf",
    local_dir=".",
)
print(f"Downloaded: {path}")
PY
fi

if [[ ! -f "$SCRIPT_DIR/$NEMOTRON" ]]; then
  echo "ERROR: $NEMOTRON missing after download." >&2
  echo "  Expected: $SCRIPT_DIR/$NEMOTRON" >&2
  exit 1
fi
ls -lh "$SCRIPT_DIR/$NEMOTRON"

echo "==> Downloading YOLO11n (PyTorch) for TensorRT export..."
"$PY" - <<'PY'
from ultralytics import YOLO
YOLO("yolo11n.pt")
print("yolo11n.pt ready")
PY

echo "==> Export YOLO11n to TensorRT engine (Jetson GPU)..."
if command -v yolo &>/dev/null; then
  yolo export model=yolo11n.pt format=engine device=0 2>/dev/null || \
    echo "WARN: TensorRT export failed – will use .pt fallback at runtime"
else
  echo "WARN: yolo CLI not found – skip TensorRT export"
fi

if [[ -f yolo11n.engine ]]; then
  echo "TensorRT engine: $SCRIPT_DIR/yolo11n.engine"
else
  echo "Using PyTorch weights; set YOLO_MODEL=models/yolo11n.pt in .env if needed"
fi

echo "==> Whisper models download on first STT run (faster-whisper)."
echo "Done. Nemotron: $SCRIPT_DIR/$NEMOTRON"
echo "Start: arif   (or: bash $ARIF_ROOT/scripts/arif)"
