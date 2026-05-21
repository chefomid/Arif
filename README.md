# Arif – Multimodal AI Chatbot for Jetson Orin Nano Super

Local-first chat UI with keyboard, mouse, push-to-talk microphone, and ELP stereo camera vision (YOLO11 + scene memory). Responses powered by **Nemotron3 Nano 4B** via `llama-server`.

**UI:** Python [NiceGUI](https://nicegui.io) (terminal-style web UI on port 8000). No Node/npm required.

## Features

- **Chat** – text input with streaming replies from Nemotron
- **Push-to-talk** – hold button or Space; live partial transcript; auto-send after 3 s silence
- **Camera** – live MJPEG view with YOLO bounding boxes
- **Scene memory** – detection timeline in RAM for environmental Q&A and rewind queries

## Architecture

```
NiceGUI (Python)  ←same process→  FastAPI backend  →  llama-server (Nemotron)
                                      ├── faster-whisper (STT)
                                      ├── OpenCV (ELP camera)
                                      └── YOLO11 TensorRT
```

## Requirements

- **Python 3.11+** (required — app will not start on 3.10; uses `StrEnum` from the stdlib)
- JetPack 6.x on Orin Nano Super (for full GPU vision + Nemotron)
- `llama-server` on Jetson (**CPU** for Nemotron on 8GB; optional GPU for YOLO)
- USB mic + ELP stereo camera (optional on dev PC)

## Quick start (Jetson)

### 1. Prerequisites

- JetPack 6.x on Orin Nano Super

**CUDA / JetPack** (if `nvcc` is missing):

```bash
cd ~/Arif
bash scripts/install-jetpack-cuda.sh        # full dev stack
# or: bash scripts/install-jetpack-cuda.sh minimal
```

**llama-server** (one time):

```bash
cd ~/Arif
bash scripts/install-llama-server.sh
```

([Jetson AI Lab – Nemotron3 Nano 4B](https://www.jetson-ai-lab.com/models/nemotron3-nano-4b/))

### 2. Setup

```bash
git clone <your-repo> ~/Arif
cd ~/Arif
bash scripts/jetson-update.sh     # pull, disk cleanup, .env, venv
```

Or step by step:

```bash
bash scripts/install-python.sh
bash scripts/configure-env.sh     # CPU-only .env (no nano needed)
bash models/download_models.sh
bash scripts/install-llama-server.sh
```

**After every `git pull` on the Nano:**

```bash
cd ~/Arif
bash scripts/jetson-update.sh
# or:  arif update
```

### 3. Models

```bash
bash models/download_models.sh
```

Set `YOLO_MODEL=models/yolo11n.engine` in `.env` after TensorRT export.

### 4. Run

```bash
arif
```

Starts **llama-server** + **backend/UI** on port **8000**. Stop with `Ctrl+C` or `arif stop`.

Open `http://<jetson-ip>:8000`.

**Manual start** (two terminals):

```bash
llama-server -m models/NVIDIA-Nemotron3-Nano-4B-Q4_K_M.gguf \
  --host 0.0.0.0 --port 8080 --n-gpu-layers 0 --ctx-size 2048 --alias nemotron
```

```bash
source .venv/bin/activate
python backend/run.py
```

## Development (Windows / Linux)

```bash
cd Arif
python scripts/setup.py          # creates .venv, installs deps (Python 3.11+)
```

**Windows:**

```powershell
.\.venv\Scripts\python.exe backend\run.py
```

**Linux / macOS:**

```bash
source .venv/bin/activate
python backend/run.py
```

Open **http://localhost:8000**.

For chat, run `llama-server` separately (see manual start above). LLM status dot stays off until port 8080 is up.

### Python version errors

If you see `cannot import name 'StrEnum' from 'enum'` or `Python 3.11+ required`:

```bash
# Jetson / Linux — one command
bash scripts/install-python.sh

# Windows — use Python 3.11+ from python.org, then:
Remove-Item -Recurse -Force .venv
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

### Keyboard navigation

| Key | Action |
|-----|--------|
| `/` | Focus message input |
| `Space` (hold) | Push-to-talk |
| `C` | Toggle camera view |
| `D` | Device picker |
| `Esc` | Back to chat |
| `?` | Help screen |

## Configuration

Copy `.env.example` to `.env`:

| Variable | Description |
|----------|-------------|
| `LLM_BASE_URL` | llama-server OpenAI API (default `http://127.0.0.1:8080/v1`) |
| `ARIF_HOST` / `ARIF_PORT` | UI server bind (default `0.0.0.0:8000`) |
| `CAMERA_DEVICE` | V4L2 index (default `0`; must exist — check with `v4l2-ctl --list-devices`) |
| `VAD_SILENCE_SECONDS` | Auto-send after PTT (default `3`) |
| `YOLO_FPS_CAP` | Max inference FPS (default `8`) |

## systemd (optional)

```bash
sudo cp deploy/systemd/nemotron-llama.service /etc/systemd/system/
sudo cp deploy/systemd/arif-backend.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now nemotron-llama arif-backend
```

## API

| Endpoint | Description |
|----------|-------------|
| `GET /` | NiceGUI web UI |
| `GET /health` | Backend + LLM status |
| `POST /api/chat` | Non-streaming chat |
| `GET /api/vision/camera/mjpeg` | Live camera stream |
| `WS /ws` | PTT, streaming chat, vision metadata (optional clients) |

## Disk full (`No space left on device`)

```bash
df -h
bash scripts/disk-cleanup.sh
# if still full:
bash scripts/disk-cleanup.sh --aggressive
git pull
```

Keep one copy of the Nemotron `.gguf` under `models/`. Remove duplicate project folders (e.g. old `Arif` clones).

## Memory tips (8 GB)

**Default: Nemotron on CPU** (`LLM_GPU_LAYERS=0`) — avoids CUDA OOM on Orin Nano 8GB. First load can take **3–6 minutes**; then chat works.

```bash
# In .env (defaults from .env.example):
ARIF_ENGAGE_GPU=false
ARIF_LLM_AUTO_FIT=false
LLM_GPU_LAYERS=0
LLM_CTX_SIZE=2048
```

- Keep Nemotron in a **separate** `llama-server` process
- Use `tiny.en` Whisper; lower `YOLO_FPS_CAP` if tight on RAM
- On failure: `arif logs` or `cat logs/llama-last.log`

### Optional: GPU mode (`ARIF_ENGAGE_GPU=true`)

Only if you have headroom and want faster inference:

```bash
ARIF_ENGAGE_GPU=true
ARIF_LLM_AUTO_FIT=true
LLM_GPU_LAYERS=auto
arif gpu-prep   # max clocks, closes browsers
arif
```

## License

Project code: MIT. Model weights follow NVIDIA / Ultralytics / OpenAI licenses respectively.
