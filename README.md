# Arif – Multimodal AI Chatbot for Jetson Orin Nano Super

Local-first chat UI with keyboard, mouse, push-to-talk microphone, and ELP stereo camera vision (YOLO11 + scene memory). Responses powered by **Nemotron3 Nano 4B** via `llama-server`.

## Features

- **Chat** – text input with streaming replies from Nemotron
- **Push-to-talk** – hold button or Space; live partial transcript; auto-send after 3 s silence
- **Camera** – live MJPEG view with YOLO bounding boxes
- **Scene memory** – detection timeline in RAM for environmental Q&A and rewind queries

## Architecture

```
React UI  ←WebSocket/REST→  FastAPI backend  →  llama-server (Nemotron)
                                ├── faster-whisper (STT)
                                ├── OpenCV (ELP camera)
                                └── YOLO11 TensorRT
```

## Quick start (Jetson)

### 1. Prerequisites

- JetPack 6.x on Orin Nano Super

**CUDA / JetPack** (on the Jetson, if `nvcc` is missing):

```bash
cd ~/Arif
bash scripts/install-jetpack-cuda.sh        # full dev stack
# or: bash scripts/install-jetpack-cuda.sh minimal   # nvcc only, smaller
```

Fresh device? Flash the [JetPack SD card image](https://developer.nvidia.com/embedded/jetpack) first, or follow the [Orin Nano JP6 initial setup](https://www.jetson-ai-lab.com/initial_setup_jon.html).
- `llama-server` built with CUDA — install once on the Jetson:

```bash
cd ~/Arif
bash scripts/install-llama-server.sh
```

([Jetson AI Lab – Nemotron3 Nano 4B](https://www.jetson-ai-lab.com/models/nemotron3-nano-4b/))
- USB mic + ELP 1200p stereo camera

### 2. Setup

```bash
git clone <your-repo> ~/Arif
cd ~/Arif
bash deploy/jetson_setup.sh
```

### 3. Models

```bash
bash models/download_models.sh
# Nemotron GGUF + YOLO11n → TensorRT engine
```

Set `YOLO_MODEL=models/yolo11n.engine` in `.env` after export.

### 4. Run everything (one command)

```bash
arif
```

This starts **llama-server** (Nemotron) and the **backend**, then prints the UI URL. Stop with `Ctrl+C` or `arif stop`.

Install the `arif` command (if you get `command not found`):

```bash
cd ~/Arif
git pull
bash scripts/install-arif.sh
source ~/.bashrc
hash -r
arif
```

**Always works** (no PATH install needed):

```bash
bash ~/Arif/scripts/arif
# or
cd ~/Arif && ./arif
# or
cd ~/Arif && npm start
```

Or after setup: `bash deploy/jetson_setup.sh` links it automatically.

**Manual start** (two terminals):

```bash
llama-server -m models/NVIDIA-Nemotron3-Nano-4B-Q4_K_M.gguf \
  --host 0.0.0.0 --port 8080 --n-gpu-layers 999 --alias nemotron
```

```bash
source .venv/bin/activate && cd backend && python run.py
```

Open `http://<jetson-ip>:8000` (production) or run `npm run dev` in `frontend/` for development.

## Development (Windows / remote)

**One command** (backend + frontend):

```bash
npm install          # first time only (root + installs concurrently)
npm run setup        # first time only (venv + Python + frontend deps)
npm run dev:all
```

Open **http://localhost:5173** — Vite proxies `/api`, `/health`, and `/ws` to port 8000.

### Plug-and-play devices

On startup the backend **auto-detects** USB/external microphone and camera (best match by name/resolution). Change devices anytime:

- Press **`D`** → device picker (↑↓ navigate, **Enter** select, **`A`** auto-detect)
- Status bar shows active mic and camera names

### Keyboard navigation (no mouse required)

| Key | Action |
|-----|--------|
| `/` | Focus message input |
| `Space` (hold) | Push-to-talk |
| `C` | Toggle camera view |
| `D` | Device picker |
| `Esc` | Back to chat |
| `?` | Help screen |

Or run separately:

```bash
npm run dev:backend   # API on :8000
npm run dev:frontend  # UI on :5173
```

## Configuration

Copy `.env.example` to `.env`:

| Variable | Description |
|----------|-------------|
| `LLM_BASE_URL` | llama-server OpenAI API (default `http://127.0.0.1:8080/v1`) |
| `CAMERA_DEVICE` | V4L2 index (default `0`) |
| `CAMERA_WIDTH` / `CAMERA_HEIGHT` | Capture size (default `1600x600` for stereo half) |
| `VAD_SILENCE_SECONDS` | Auto-send delay after PTT release (default `3`) |
| `YOLO_FPS_CAP` | Max inference FPS (default `8`) |

## ELP stereo camera

The ELP 1200p typically outputs a side-by-side frame (e.g. 3200×1200). The backend splits into left/right; **YOLO runs on the left view**. Adjust `CAMERA_WIDTH`/`CAMERA_HEIGHT` if your device reports different modes (`v4l2-ctl --list-formats-ext`).

## systemd (optional)

Edit user paths in `deploy/systemd/*.service`, then:

```bash
sudo cp deploy/systemd/nemotron-llama.service /etc/systemd/system/
sudo cp deploy/systemd/arif-backend.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now nemotron-llama arif-backend
```

## API

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Backend + LLM status |
| `POST /api/chat` | Send chat message |
| `GET /api/vision/camera/mjpeg` | Live camera stream |
| `GET /api/vision/memory/query?minutes=5` | Query scene memory |
| `WS /ws` | PTT, chat streaming, vision metadata |

## Memory tips (8 GB)

- Keep Nemotron in a **separate** `llama-server` process
- Use `tiny.en` Whisper first; upgrade to `base.en` if accuracy is insufficient
- Lower `YOLO_FPS_CAP` if you see OOM or thermal throttling

## License

Project code: MIT. Model weights follow NVIDIA / Ultralytics / OpenAI licenses respectively.
