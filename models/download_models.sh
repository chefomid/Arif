#!/usr/bin/env bash
# Download Nemotron GGUF + YOLO11n weights
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
  exit 1
fi
ls -lh "$SCRIPT_DIR/$NEMOTRON"

echo "==> Downloading YOLO11n..."
"$PY" -m pip install -q ultralytics
"$PY" - <<'PY'
import shutil
from pathlib import Path
from ultralytics import YOLO

dst = Path("yolo11n.pt")
if not dst.exists():
    m = YOLO("yolo11n.pt")
    src = Path(getattr(m, "ckpt_path", None) or "yolo11n.pt")
    if src.resolve() != dst.resolve() and src.exists():
        shutil.copy2(src, dst)
print(f"YOLO weights: {dst.resolve()}")
PY

echo "==> Optional: export TensorRT engine on Jetson GPU"
if command -v yolo &>/dev/null; then
  yolo export model=yolo11n.pt format=engine device=0 2>/dev/null && \
    mv -f yolo11n.engine "$SCRIPT_DIR/yolo11n.engine" 2>/dev/null || \
    echo "WARN: TensorRT export skipped or failed — use models/yolo11n.pt"
fi

echo "Done."
echo "  Detect: arif detect"
echo "  Chat:   start llama-server, then arif chat"
