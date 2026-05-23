# Arif

Two standalone CLI tools for Jetson Orin Nano (or any PC with Python 3.11+):

| Command | What it does |
|---------|----------------|
| `arif detect` | Webcam + YOLO — GUI window showing **person** detections |
| `arif chat` | Terminal chatbot via **Nemotron** (GGUF + `llama-server`) |

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

Start the LLM server first (separate terminal):

```bash
llama-server -m models/NVIDIA-Nemotron3-Nano-4B-Q4_K_M.gguf \
  --host 127.0.0.1 --port 8080 --n-gpu-layers 0 --ctx-size 2048 --alias nemotron
```

Then chat:

```bash
arif chat
```

Type `quit` or press Ctrl+C to exit.

## Configuration

Copy `.env.example` to `.env`:

| Variable | Description |
|----------|-------------|
| `YOLO_MODEL` | YOLO weights (`.pt` or `.engine`) |
| `CAMERA_DEVICE` | Webcam index (default `0`) |
| `YOLO_CONFIDENCE` | Detection threshold (default `0.4`) |
| `LLM_BASE_URL` | llama-server OpenAI API (default `http://127.0.0.1:8080/v1`) |
| `LLM_MODEL` | Model alias (default `nemotron`) |

## License

MIT. Model weights follow NVIDIA / Ultralytics licenses.
