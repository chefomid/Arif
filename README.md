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

- **Python 3.11+** (uses `StrEnum` and modern typing)
- JetPack 6.x on Orin Nano Super (for full GPU vision + Nemotron)
- `llama-server` with CUDA on Jetson
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
bash deploy/jetson_setup.sh
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
  --host 0.0.0.0 --port 8080 --n-gpu-layers 999 --alias nemotron
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
| `CAMERA_DEVICE` | V4L2 index (default `0`) |
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

## Memory tips (8 GB)

- Keep Nemotron in a **separate** `llama-server` process
- Use `tiny.en` Whisper first; upgrade to `base.en` if needed
- Lower `YOLO_FPS_CAP` if OOM or thermal throttling

## License

Project code: MIT. Model weights follow NVIDIA / Ultralytics / OpenAI licenses respectively.
