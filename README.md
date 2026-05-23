# Arif

Two standalone CLI tools for Jetson Orin Nano (or any PC with Python 3.11+):

| Command | What it does |
|---------|----------------|
| `arif detect` | Webcam + YOLO — GUI window showing **person** detections |
| `arif chat` | Terminal chatbot — **starts llama-server automatically**, then chats |
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

One command — starts `llama-server` if needed, then opens chat:

```bash
arif chat
# or simply:
arif
# or:
python chat.py
```

First model load on 8GB Jetson (CPU) can take **3–6 minutes**. Logs: `logs/llama-last.log`.

Type `quit` or press Ctrl+C to exit (stops llama-server if this command started it).

## Configuration

Copy `.env.example` to `.env`:

| Variable | Description |
|----------|-------------|
| `YOLO_MODEL` | YOLO weights (`.pt` or `.engine`) |
| `CAMERA_DEVICE` | Webcam index (default `0`) |
| `YOLO_CONFIDENCE` | Detection threshold (default `0.4`) |
| `LLM_BASE_URL` | llama-server OpenAI API (default `http://127.0.0.1:8080/v1`) |
| `LLM_MODEL` | Model alias (default `nemotron`) |
| `LLM_MODEL_PATH` | Nemotron GGUF path |
| `LLM_GPU_LAYERS` | `0` = CPU-only on 8GB Jetson (default) |
| `LLM_CTX_SIZE` | Context size (default `2048`) |

## License

MIT. Model weights follow NVIDIA / Ultralytics licenses.
