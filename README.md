# Arif

Two standalone CLI tools for Jetson Orin Nano (or any PC with Python 3.11+):

| Command | What it does |
|---------|----------------|
| `arif detect` | Webcam + YOLO — GUI window showing **person** detections |
| `arif chat` | Terminal chat — pick **1=light (fast)** or **2=heavy (Nemotron)** |
| `arif` | Same as `arif chat` |

No web UI, no microphone, no scene memory — just two simple features you run separately.

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

## 1. Person detection (YOLO)

```bash
arif detect
```

Opens an OpenCV window. Press **Q** to quit.

Options:

```bash
arif detect --camera 0 --model models/yolo11n.pt --conf 0.4
```

On Jetson, use a TensorRT engine for speed: set `YOLO_MODEL=models/yolo11n.engine` in `.env`.

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

## Configuration

Copy `.env.example` to `.env`:

| Variable | Description |
|----------|-------------|
| `YOLO_MODEL` | YOLO weights (`.pt` or `.engine`) |
| `CAMERA_DEVICE` | Webcam index (default `0`) |
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
