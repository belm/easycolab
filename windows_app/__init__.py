"""EasyColab Windows Native Desktop Client (PySide6 / Qt6)."""
from __future__ import annotations

import sys
from pathlib import Path


def _read_version(default: str = "1.1.0") -> str:
    candidates = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(Path(meipass) / "VERSION")
    pkg_dir = Path(__file__).resolve().parent
    candidates.append(pkg_dir.parent / "VERSION")
    candidates.append(pkg_dir / "VERSION")
    for p in candidates:
        try:
            if p.is_file():
                val = p.read_text(encoding="utf-8").strip()
                if val:
                    return val
        except Exception:
            pass
    return default


__version__ = _read_version()
