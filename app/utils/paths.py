from __future__ import annotations
import sys
from pathlib import Path

def app_dir() -> Path:
    if "__compiled__" in globals():
        return Path(sys.argv[0]).resolve().parent
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]

def resource_path(relative: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", app_dir()))
    return base / relative
