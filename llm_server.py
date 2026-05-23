"""Start llama-server when needed and stop it on exit."""
from __future__ import annotations

import atexit
import json
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
    "cudamalloc failed",
    "nvmapmemalloc",
    "failed to allocate cuda",
    "failed to create context with model",
)

FATAL_MARKERS = (
    "invalid device",
    "error while handling argument",
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


def _is_light_model(model_path: str) -> bool:
    name = model_path.lower()
    return any(x in name for x in ("0.5b", "360m", "tiny", "smollm", "1b-instruct"))


def default_ready_timeout(gpu_layers: int, model_path: str) -> int:
    if _is_light_model(model_path):
        return 300 if is_jetson() else 120
    if is_jetson() and gpu_layers == 0:
        return 900
    if gpu_layers == 0:
        return 600
    return 180


def loaded_model_ids(base_url: str) -> list[str]:
    try:
        with urllib.request.urlopen(f"{_llm_root(base_url)}/v1/models", timeout=5) as resp:
            data = json.loads(resp.read().decode())
        return [m.get("id", "") for m in data.get("data", []) if m.get("id")]
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError, ValueError):
        return []


def stop_llama_server(port: int = 8080) -> None:
    """Stop llama-server we started, or any instance on this port."""
    _stop_started()
    subprocess.run(
        ["pkill", "-f", f"llama-server.*--port {port}"],
        capture_output=True,
    )
    subprocess.run(
        ["pkill", "-f", f"llama-server.*{port}"],
        capture_output=True,
    )
    time.sleep(1)


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
    """Only pass flags known to be safe across llama.cpp versions."""
    help_text = _llama_help_text(llama_bin)
    extra: list[str] = []
    if "--parallel" in help_text:
        extra.extend(["--parallel", "1"])
    return extra


def _subprocess_env(gpu_layers: int, hide_cuda: bool) -> dict[str, str]:
    env = os.environ.copy()
    if gpu_layers == 0 and hide_cuda:
        env["CUDA_VISIBLE_DEVICES"] = "-1"
    return env


def _tail_log(log_file: Path, lines: int = 30) -> str:
    if not log_file.is_file():
        return "(no log file)"
    text = log_file.read_text(encoding="utf-8", errors="replace")
    return "\n".join(text.splitlines()[-lines:])


def _log_matches(log_file: Path, markers: tuple[str, ...], lines: int = 80) -> bool:
    if not log_file.is_file():
        return False
    text = _tail_log(log_file, lines=lines).lower()
    return any(marker in text for marker in markers)


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
    if _log_matches(log_file, OOM_MARKERS):
        print("  CUDA/RAM OOM — close other apps; set LLM_CTX_SIZE=512 in .env", file=sys.stderr)
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
        if _log_matches(log_file, OOM_MARKERS) or _log_matches(log_file, FATAL_MARKERS, lines=40):
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
    hide_cuda: bool,
    model_path: Path,
    model_alias: str,
) -> None:
    global _started

    cmd = [
        str(llama_bin),
        "-m",
        str(model_path),
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
        model_alias,
    ]

    env = _subprocess_env(settings.llm_gpu_layers, hide_cuda)
    with log_file.open("w", encoding="utf-8") as log:
        _started = subprocess.Popen(
            cmd,
            stdout=log,
            stderr=subprocess.STDOUT,
            cwd=ROOT,
            env=env,
        )


def ensure_llama_server(settings: Settings | None = None) -> None:
    """Reuse running server with the right model, or start llama-server."""
    settings = settings or get_settings()
    base_url = settings.llm_base_url
    model_path = ROOT / settings.llm_model_path
    model_alias = settings.llm_model

    if llm_ready(base_url):
        loaded = loaded_model_ids(base_url)
        if model_alias in loaded:
            print(f"Using llama-server ({model_alias}).", file=sys.stderr)
            return
        print(f"Switching model to {model_alias} — restarting server …", file=sys.stderr)
        parsed = urlparse(base_url)
        stop_llama_server(parsed.port or 8080)

    llama_bin = find_llama_server()
    if llama_bin is None:
        print("llama-server not found.", file=sys.stderr)
        print("Install on Jetson: bash scripts/install-llama-server.sh", file=sys.stderr)
        sys.exit(1)

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

    timeout = settings.llm_ready_timeout_sec or default_ready_timeout(
        settings.llm_gpu_layers, settings.llm_model_path
    )
    ctx_sizes = _ctx_tiers(settings.llm_ctx_size)
    hide_cuda_options = (False, True) if settings.llm_gpu_layers == 0 else (False,)

    atexit.register(_stop_started)
    signal.signal(signal.SIGINT, _on_signal)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _on_signal)

    label = "light" if _is_light_model(settings.llm_model_path) else "heavy"
    print(f"Loading {label} model: {model_path.name}", file=sys.stderr)

    for hide_cuda in hide_cuda_options:
        for attempt, ctx_size in enumerate(ctx_sizes, start=1):
            _stop_started()
            mode = "hide GPU" if hide_cuda else "standard CPU"
            if attempt > 1 or hide_cuda:
                print(f"Retrying llama-server ({mode}, ctx={ctx_size}) …", file=sys.stderr)
            else:
                wait_hint = "1–3 min" if _is_light_model(settings.llm_model_path) else "several minutes"
                print(f"Starting llama-server (first load can take {wait_hint}) …", file=sys.stderr)

            print(
                f"  model={model_alias}  ctx={ctx_size}  n-gpu-layers={settings.llm_gpu_layers}  mode={mode}",
                file=sys.stderr,
            )
            print(f"  timeout: {timeout}s  log: {log_file}", file=sys.stderr)

            _launch_llama(
                llama_bin,
                settings,
                host,
                port,
                ctx_size,
                log_file,
                hide_cuda,
                model_path,
                model_alias,
            )

            if wait_for_llm(base_url, timeout, log_file):
                print("llama-server ready.", file=sys.stderr)
                return

            if _log_matches(log_file, FATAL_MARKERS, lines=40):
                _report_failure(log_file, timeout, reason="llama-server rejected startup flags.")
                _stop_started()
                sys.exit(1)

            oom = _log_matches(log_file, OOM_MARKERS)
            if oom and (attempt < len(ctx_sizes) or hide_cuda != hide_cuda_options[-1]):
                print("OOM during load — trying next config …", file=sys.stderr)
                continue

    _report_failure(log_file, timeout, reason="llama-server failed to start (see log).")
    _stop_started()
    sys.exit(1)
