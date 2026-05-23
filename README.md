# Arif

Three standalone CLI tools for Jetson Orin Nano (or any PC with Python 3.11+):

| Command | What it does |
|---------|----------------|
| `arif detect` | YOLO person detection + **stereo distance (m)** on ELP camera |
| `arif chat` | Terminal chat — pick **1=light (fast)** or **2=heavy (Nemotron)** |
| `arif see` | **Chat + live camera** — ask "can you see me?" |
| `arif` | Same as `arif chat` |

No web UI — three features you run separately.

## Setup

```bash
git clone https://github.com/chefomid/Arif.git
cd Arif
python setup.py              # creates .venv, installs deps
cp .env.example .env         # optional
bash models/download_models.sh
```

**Windows:**

```powershell
py -3.12 setup.py
copy .env.example .env
.\arif.bat detect
```

**Jetson — llama-server** (one time):

```bash
bash scripts/install-llama-server.sh
```

## 1. Person detection + distance (YOLO + stereo)

```bash
arif detect
```

- Detects **person** on the **left** lens of a side-by-side stereo camera
- Shows distance in meters on each box (e.g. `person 85% 2.3m`)
- Auto-uses `yolo11n.engine` if present (faster on Jetson)
- Press **Q** to quit

**Faster on Jetson:**

```bash
cd models && yolo export model=yolo11n.pt format=engine device=0
# .env: YOLO_MODEL=models/yolo11n.engine
sudo jetson_clocks
```

**Tune stereo in `.env`** (ELP ~60mm baseline is a starting point):

| Variable | Default | Meaning |
|----------|---------|---------|
| `CAMERA_STEREO` | `true` | Split frame left/right |
| `STEREO_BASELINE_M` | `0.06` | Lens spacing (meters) |
| `STEREO_FOCAL_PX` | `500` | Focal length in pixels (calibrate for accuracy) |
| `YOLO_IMGSZ` | `416` | Smaller = faster |
| `YOLO_FRAME_SKIP` | `2` | Run YOLO every N frames |

```bash
arif detect --camera 0 --imgsz 320 --skip 3
arif detect --no-stereo   # YOLO only, no distance
```

## 2. Terminal chat

```bash
arif chat
```

You'll see:

```
Arif is online.

Choose model:
  1 = Light  — fast replies (Qwen 0.5B)
  2 = Heavy  — better quality (Nemotron 4B)

Type 1 or 2 and press Enter:
```

- **1 (light)** — loads in ~1–3 min, faster replies (good default on 8GB Jetson)
- **2 (heavy)** — Nemotron 4B, slower load (~10–15 min) but better answers

Logs: `logs/llama-last.log`. Type `quit` or Ctrl+C to exit.

## 3. See + chat (vision + dialogue)

```bash
arif see
```

Starts the camera in the background, then chat. Pick model **1 (light recommended)**.

Try asking:
- "Can you see me?"
- "How far away am I?"
- "Is anyone there?"

Arif answers from **live YOLO detections** — yes if a person is in frame, with distance when stereo is calibrated.

**Tip on 8GB Jetson:** use model **1**, `yolo11n.engine`, and close other apps. Don't run `detect` and `see` at the same time.

## Configuration

Copy `.env.example` to `.env`:

| Variable | Description |
|----------|-------------|
| `YOLO_MODEL` | YOLO weights (auto-picks `.engine` if next to `.pt`) |
| `CAMERA_DEVICE` / `CAMERA_WIDTH` / `CAMERA_HEIGHT` | ELP stereo defaults `0`, `1600`, `600` |
| `CAMERA_STEREO` | Side-by-side depth (default `true`) |
| `STEREO_BASELINE_M` / `STEREO_FOCAL_PX` | Depth calibration |
| `YOLO_IMGSZ` / `YOLO_FRAME_SKIP` | Speed tuning |
| `YOLO_CONFIDENCE` | Detection threshold (default `0.4`) |
| `LLM_BASE_URL` | llama-server OpenAI API (default `http://127.0.0.1:8080/v1`) |
| `LLM_LIGHT_MODEL_PATH` | Fast model GGUF (default Qwen 0.5B) |
| `LLM_HEAVY_MODEL_PATH` | Nemotron GGUF |
| `LLM_GPU_LAYERS` | `0` = CPU-only on 8GB Jetson (default) |
| `LLM_LIGHT_CTX_SIZE` / `LLM_HEAVY_CTX_SIZE` | Context per model (512 / 1024) |
| `LLM_READY_TIMEOUT_SEC` | Max wait (0 = auto) |

### CUDA OOM on Jetson (`cudaMalloc failed`)

Ensure `.env` has `LLM_GPU_LAYERS=0`. Close browser and other apps, then retry with **1 (light)** first.

## License

MIT. Model weights follow NVIDIA / Ultralytics licenses.
