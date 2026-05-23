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

_started: subprocess.Popen | None = None


def _llm_root(base_url: str) -> str:
    return base_url.rstrip("/").removesuffix("/v1")


def llm_ready(base_url: str) -> bool:
    root = _llm_root(base_url)
    for path in ("/health", "/v1/models"):
        try:
            with urllib.request.urlopen(f"{root}{path}", timeout=3) as resp:
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


def wait_for_llm(base_url: str, timeout: int) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if llm_ready(base_url):
            return True
        if _started is not None and _started.poll() is not None:
            return False
        time.sleep(2)
    return False


def ensure_llama_server(settings: Settings | None = None) -> None:
    """Reuse running server or start llama-server and register cleanup."""
    global _started

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

    cmd = [
        str(llama_bin),
        "-m",
        str(model_path),
        "--host",
        host,
        "--port",
        str(port),
        "--ctx-size",
        str(settings.llm_ctx_size),
        "--n-gpu-layers",
        str(settings.llm_gpu_layers),
        "--alias",
        settings.llm_model,
    ]

    print("Starting llama-server (first load can take several minutes) …", file=sys.stderr)
    print(f"  log: {log_file}", file=sys.stderr)

    with log_file.open("w", encoding="utf-8") as log:
        _started = subprocess.Popen(
            cmd,
            stdout=log,
            stderr=subprocess.STDOUT,
            cwd=ROOT,
        )

    atexit.register(_stop_started)
    signal.signal(signal.SIGINT, _on_signal)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _on_signal)

    timeout = 360 if settings.llm_gpu_layers == 0 else 180
    if not wait_for_llm(base_url, timeout):
        print("llama-server did not become ready in time.", file=sys.stderr)
        print(f"Check: tail -40 {log_file}", file=sys.stderr)
        _stop_started()
        sys.exit(1)

    print("llama-server ready.", file=sys.stderr)
