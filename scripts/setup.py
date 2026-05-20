#!/usr/bin/env python3
"""Create venv and install Arif dependencies (Python 3.11+)."""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VENV = ROOT / ".venv"
REQUIREMENTS = ROOT / "backend" / "requirements.txt"


def main() -> None:
    if sys.version_info < (3, 11):
        print(f"ERROR: Python 3.11+ required (found {sys.version.split()[0]})")
        sys.exit(1)

    py = sys.executable
    venv_py = VENV / ("Scripts" if sys.platform == "win32" else "bin") / (
        "python.exe" if sys.platform == "win32" else "python"
    )
    venv_pip = VENV / ("Scripts" if sys.platform == "win32" else "bin") / (
        "pip.exe" if sys.platform == "win32" else "pip"
    )

    print("==> Creating Python virtualenv...")
    if not venv_py.exists():
        subprocess.check_call([py, "-m", "venv", str(VENV)])

    print("==> Installing backend dependencies...")
    subprocess.check_call([str(venv_py), "-m", "pip", "install", "--upgrade", "pip"])
    subprocess.check_call([str(venv_py), "-m", "pip", "install", "-r", str(REQUIREMENTS)])

    env_file = ROOT / ".env"
    example = ROOT / ".env.example"
    if not env_file.exists() and example.exists():
        shutil.copy(example, env_file)
        print("==> Created .env from .env.example")

    print("\nSetup complete.")
    print("  Windows:  .venv\\Scripts\\python.exe backend\\run.py")
    print("  Linux:    source .venv/bin/activate && python backend/run.py")
    print("  Jetson:   arif")


if __name__ == "__main__":
    main()
