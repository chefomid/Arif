"""Ensure Python 3.11+ before importing app code (StrEnum, etc.)."""
import sys

MIN_VERSION = (3, 11)


def require_python() -> None:
    if sys.version_info < MIN_VERSION:
        ver = ".".join(map(str, sys.version_info[:3]))
        print(
            f"ERROR: Python 3.11+ required (running {ver}).\n"
            "  Windows: install from https://www.python.org/downloads/\n"
            "  Jetson:  bash scripts/install-python.sh",
            file=sys.stderr,
        )
        sys.exit(1)
