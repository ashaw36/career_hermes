"""
CareerCraft Agent — path helpers.

Resolve writable application data paths for source runs, PyInstaller bundles,
and restricted environments where the user home directory is read-only.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from typing import List


def _is_writable_dir(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".write_test"
        probe.write_text("", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return True
    except OSError:
        return False


def get_app_data_dir() -> Path:
    """Return a writable persistent-ish directory for config, DB, and secrets."""
    candidates: List[Path] = []

    configured = os.getenv("CC_CONFIG_DIR") or os.getenv("CAREERCRAFT_HOME")
    if configured:
        candidates.append(Path(configured).expanduser())

    home = Path.home()
    if sys.platform == "win32":
        appdata = os.getenv("APPDATA")
        if appdata:
            candidates.append(Path(appdata) / "CareerCraft")
        candidates.append(home / "AppData" / "Roaming" / "CareerCraft")
    elif sys.platform == "darwin":
        candidates.append(home / "Library" / "Application Support" / "CareerCraft")
    else:
        xdg_data = os.getenv("XDG_DATA_HOME")
        if xdg_data:
            candidates.append(Path(xdg_data) / "careercraft")
        candidates.append(home / ".careercraft")

    candidates.extend(
        [
            Path.cwd() / ".careercraft",
            Path(tempfile.gettempdir()) / "careercraft",
        ]
    )

    for candidate in candidates:
        if _is_writable_dir(candidate):
            return candidate

    fallback = Path(tempfile.gettempdir()) / "careercraft"
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


def get_default_export_dir() -> Path:
    """Return a writable default directory for generated resume exports."""
    documents = Path.home() / "Documents" / "CareerCraft"
    if _is_writable_dir(documents):
        return documents
    return get_app_data_dir() / "exports"
