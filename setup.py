#!/usr/bin/env python3
"""Create venv and install Arif dependencies (Python 3.11+)."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"
REQUIREMENTS = ROOT / "requirements.txt"


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

    print(f"==> Using Python {sys.version.split()[0]}")
    print("==> Creating virtualenv...")
    if not venv_py.exists():
        subprocess.check_call([py, "-m", "venv", str(VENV)])

    r = subprocess.run(
        [str(venv_py), "-c", "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)"],
        capture_output=True,
    )
    if r.returncode != 0:
        print("ERROR: .venv uses Python < 3.11. Remove .venv and re-run setup.")
        sys.exit(1)

    print("==> Installing dependencies...")
    subprocess.check_call([str(venv_pip), "install", "-r", str(REQUIREMENTS)])
    print("Done. Activate .venv then run: arif detect  or  arif chat")


if __name__ == "__main__":
    main()
