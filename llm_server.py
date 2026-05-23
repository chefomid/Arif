"""Start llama-server when needed and stop it on exit."""
from __future__ import annotations

import atexit
import os
import shutil
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

from config import ROOT, Settings, get_settings

LLAMA_SEARCH_PATHS = (
    "/usr/local/bin/llama-server",
    Path.home() / "llama.cpp/build/bin/llama-server",
    "/opt/llama.cpp/build/bin/llama-server",
    "/opt/llama.cpp/llama-server",
)

OOM_MARKERS = (
    "out of memory",
    "cudaMalloc failed",
    "nvmapmemalloc",
    "failed to allocate cuda",
    "failed to create context with model",
)

_started: subprocess.Popen | None = None
_llama_help: str | None = None


def _llm_root(base_url: str) -> str:
    return base_url.rstrip("/").removesuffix("/v1")


def is_jetson() -> bool:
    try:
        with open("/proc/device-tree/model", encoding="utf-8", errors="ignore") as f:
            model = f.read().lower()
        return "jetson" in model or "tegra" in model
    except OSError:
        return Path("/etc/nv_tegra_release").exists()


def default_ready_timeout(gpu_layers: int) -> int:
    if is_jetson() and gpu_layers == 0:
        return 900
    if gpu_layers == 0:
        return 600
    return 180


def llm_ready(base_url: str) -> bool:
    root = _llm_root(base_url)
    for path in ("/health", "/v1/models", "/"):
        try:
            with urllib.request.urlopen(f"{root}{path}", timeout=5) as resp:
                if resp.status == 200:
                    return True
        except (urllib.error.URLError, TimeoutError, OSError):
            continue
    return False


def find_llama_server() -> Path | None:
    found = shutil.which("llama-server")
    if found:
        return Path(found)
    for candidate in LLAMA_SEARCH_PATHS:
        path = Path(candidate)
        if path.is_file() and os.access(path, os.X_OK):
            return path
    return None


def _llama_help_text(llama_bin: Path) -> str:
    global _llama_help
    if _llama_help is None:
        try:
            proc = subprocess.run(
                [str(llama_bin), "--help"],
                capture_output=True,
                text=True,
                timeout=15,
            )
            _llama_help = (proc.stdout or "") + (proc.stderr or "")
        except (subprocess.SubprocessError, OSError):
            _llama_help = ""
    return _llama_help


def _llama_extra_args(llama_bin: Path) -> list[str]:
    help_text = _llama_help_text(llama_bin)
    extra: list[str] = []
    if "--device" in help_text:
        extra.extend(["--device", "CPU"])
    if "--parallel" in help_text:
        extra.extend(["--parallel", "1"])
    return extra


def _subprocess_env(gpu_layers: int) -> dict[str, str]:
    env = os.environ.copy()
    if gpu_layers == 0:
        # Hide GPU so CUDA-built llama.cpp stays on CPU (fixes Jetson OOM).
        env["CUDA_VISIBLE_DEVICES"] = "-1"
        env["GGML_CUDA"] = "0"
    return env


def _tail_log(log_file: Path, lines: int = 30) -> str:
    if not log_file.is_file():
        return "(no log file)"
    text = log_file.read_text(encoding="utf-8", errors="replace")
    return "\n".join(text.splitlines()[-lines:])


def _log_indicates_oom(log_file: Path) -> bool:
    if not log_file.is_file():
        return False
    text = _tail_log(log_file, lines=80).lower()
    return any(marker in text for marker in OOM_MARKERS)


def _stop_started() -> None:
    global _started
    if _started is None or _started.poll() is not None:
        _started = None
        return
    print("\nStopping llama-server …", file=sys.stderr)
    _started.terminate()
    try:
        _started.wait(timeout=15)
    except subprocess.TimeoutExpired:
        _started.kill()
        _started.wait(timeout=5)
    _started = None


def _on_signal(signum: int, _frame: object) -> None:
    _stop_started()
    raise SystemExit(128 + signum)


def _report_failure(log_file: Path, timeout: int, reason: str = "") -> None:
    print(reason or "llama-server did not become ready in time.", file=sys.stderr)
    print(f"  waited: {timeout}s", file=sys.stderr)
    if _started is not None and _started.poll() is not None:
        print(f"  process exited with code: {_started.returncode}", file=sys.stderr)
    print(f"  log: {log_file}", file=sys.stderr)
    if _log_indicates_oom(log_file):
        print("  CUDA/RAM OOM detected — close other apps; use LLM_GPU_LAYERS=0", file=sys.stderr)
        print("  and try LLM_CTX_SIZE=1024 in .env", file=sys.stderr)
    if is_jetson():
        print("  Jetson: free RAM with 'free -h'; close browser/desktop apps.", file=sys.stderr)
    tail = _tail_log(log_file)
    if tail.strip():
        print("\n--- last log lines ---", file=sys.stderr)
        print(tail, file=sys.stderr)


def wait_for_llm(base_url: str, timeout: int, log_file: Path) -> bool:
    start = time.time()
    last_progress = 0.0
    while time.time() - start < timeout:
        if llm_ready(base_url):
            return True
        if _started is not None and _started.poll() is not None:
            return False
        if _log_indicates_oom(log_file):
            return False
        now = time.time()
        if now - last_progress >= 30:
            elapsed = int(now - start)
            print(f"  still loading… {elapsed}s / {timeout}s", file=sys.stderr)
            last_progress = now
        time.sleep(2)
    return False


def _ctx_tiers(requested: int) -> list[int]:
    tiers: list[int] = []
    for size in (requested, 1024, 512):
        if size not in tiers and size > 0:
            tiers.append(size)
    return tiers


def _launch_llama(
    llama_bin: Path,
    settings: Settings,
    host: str,
    port: int,
    ctx_size: int,
    log_file: Path,
) -> None:
    global _started

    cmd = [
        str(llama_bin),
        "-m",
        str(ROOT / settings.llm_model_path),
        "--host",
        host,
        "--port",
        str(port),
        "--ctx-size",
        str(ctx_size),
        "--n-gpu-layers",
        str(settings.llm_gpu_layers),
        *_llama_extra_args(llama_bin),
        "--alias",
        settings.llm_model,
    ]

    env = _subprocess_env(settings.llm_gpu_layers)
    with log_file.open("w", encoding="utf-8") as log:
        _started = subprocess.Popen(
            cmd,
            stdout=log,
            stderr=subprocess.STDOUT,
            cwd=ROOT,
            env=env,
        )


def ensure_llama_server(settings: Settings | None = None) -> None:
    """Reuse running server or start llama-server and register cleanup."""
    settings = settings or get_settings()
    base_url = settings.llm_base_url

    if llm_ready(base_url):
        print("Using llama-server already running.", file=sys.stderr)
        return

    llama_bin = find_llama_server()
    if llama_bin is None:
        print("llama-server not found.", file=sys.stderr)
        print("Install on Jetson: bash scripts/install-llama-server.sh", file=sys.stderr)
        sys.exit(1)

    model_path = ROOT / settings.llm_model_path
    if not model_path.is_file():
        print(f"Model not found: {model_path}", file=sys.stderr)
        print("Run: bash models/download_models.sh", file=sys.stderr)
        sys.exit(1)

    parsed = urlparse(base_url)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 8080

    log_dir = ROOT / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "llama-last.log"

    timeout = settings.llm_ready_timeout_sec or default_ready_timeout(settings.llm_gpu_layers)
    ctx_sizes = _ctx_tiers(settings.llm_ctx_size)

    atexit.register(_stop_started)
    signal.signal(signal.SIGINT, _on_signal)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _on_signal)

    for attempt, ctx_size in enumerate(ctx_sizes, start=1):
        _stop_started()
        if attempt > 1:
            print(f"Retrying with smaller context (ctx={ctx_size}) …", file=sys.stderr)

        print("Starting llama-server (first load can take several minutes) …", file=sys.stderr)
        print(
            f"  ctx={ctx_size}  n-gpu-layers={settings.llm_gpu_layers}  "
            f"cpu-only={'yes' if settings.llm_gpu_layers == 0 else 'no'}",
            file=sys.stderr,
        )
        print(f"  timeout: {timeout}s  log: {log_file}", file=sys.stderr)
        if is_jetson() and settings.llm_gpu_layers == 0:
            print("  Jetson: CUDA hidden — pure CPU mode to avoid OOM.", file=sys.stderr)

        _launch_llama(llama_bin, settings, host, port, ctx_size, log_file)

        if wait_for_llm(base_url, timeout, log_file):
            print("llama-server ready.", file=sys.stderr)
            return

        oom = _log_indicates_oom(log_file)
        crashed = _started is not None and _started.poll() is not None
        if oom and attempt < len(ctx_sizes):
            print("OOM during load — trying smaller context …", file=sys.stderr)
            continue
        if crashed or oom:
            _report_failure(
                log_file,
                timeout,
                reason="llama-server failed to start (see log).",
            )
            _stop_started()
            sys.exit(1)

    _report_failure(log_file, timeout)
    _stop_started()
    sys.exit(1)
