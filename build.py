"""
CareerCraft Agent - PyInstaller Build Script

Supports two entry points:
  - WebView (default): python build.py
  - Native:            python build.py --native

Output: dist/CareerCraftAgent/
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


def get_project_root() -> Path:
    return Path(__file__).parent.resolve()


def detect_separator() -> str:
    """PyInstaller --add-data separator: Windows uses ;, Linux/macOS uses :"""
    return ";" if sys.platform == "win32" else ":"


def build(native: bool = False) -> None:
    """Build the application"""
    project_root = get_project_root()
    dist_dir = project_root / "dist"
    build_dir = project_root / "build"
    sep = detect_separator()

    # Clean old builds
    for d in (build_dir, dist_dir):
        if d.exists():
            print(f"Clean: {d}")
            shutil.rmtree(d)

    # Check PyInstaller
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("Error: PyInstaller not installed")
        print("Run: pip install pyinstaller")
        sys.exit(1)

    entry = "src/main.py" if native else "src/main_webview.py"
    name = "CareerCraftAgent"

    # Base command
    cmd: list[str] = [
        sys.executable, "-m", "PyInstaller",
        "--name", name,
        "--onedir",
        "--windowed",
        "--clean",
        "--noconfirm",
    ]

    # Data files (HTML prototype + templates + assets)
    data_files = [
        ("prototype", "prototype"),
        ("src/ui/templates", "src/ui/templates"),
    ]
    for src, dst in data_files:
        src_path = project_root / src
        if src_path.exists():
            cmd.extend(["--add-data", f"{src_path}{sep}{dst}"])

    # Assets dir (if exists)
    assets_path = project_root / "src" / "assets"
    if assets_path.exists():
        cmd.extend(["--add-data", f"{assets_path}{sep}src/assets"])

    # Hidden imports
    hidden_imports = [
        "sqlalchemy.ext.asyncio",
        "jinja2",
        "keyring",
        "httpx",
        "pydantic",
        "yaml",
        "PySide6",
        "PySide6.QtWebEngineWidgets",
        "PySide6.QtWebChannel",
        "PySide6.QtWebEngineCore",
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
        "fpdf",
    ]
    for mod in hidden_imports:
        cmd.extend(["--hidden-import", mod])

    # Collect all PySide6 (ensure QtWebEngine process and resources are bundled)
    cmd.extend(["--collect-all", "PySide6"])

    # Entry point
    cmd.append(str(project_root / entry))

    print("=" * 60)
    print(f"Building: {name}")
    print(f"Entry: {entry}")
    print(f"Platform: {sys.platform}")
    print("=" * 60)
    print(f"Command:\n{' '.join(cmd)}")
    print()

    result = subprocess.run(cmd, cwd=project_root)
    if result.returncode != 0:
        print("[ERROR] Build failed!")
        sys.exit(1)

    # Verify output
    exe_dir = dist_dir / name
    if not exe_dir.exists():
        print(f"[WARN] Output dir not found: {exe_dir}")
        sys.exit(1)

    print()
    print("[OK] Build completed!")
    print(f"Output dir: {exe_dir}")

    # List key files
    print("\nKey files check:")
    key_files = [name + ".exe" if sys.platform == "win32" else name]
    prototype_dir = exe_dir / "prototype"
    if prototype_dir.exists():
        print(f"  [OK] prototype/ included ({len(list(prototype_dir.iterdir()))} files)")
    else:
        print("  [WARN] prototype/ not found")

    for f in key_files:
        p = exe_dir / f
        if p.exists():
            size_mb = p.stat().st_size / (1024 * 1024)
            print(f"  [OK] {f} ({size_mb:.1f} MB)")
        else:
            print(f"  [WARN] {f} not found")

    print("\nLaunch:")
    if sys.platform == "win32":
        print(f"  Double-click: {exe_dir / (name + '.exe')}")
    else:
        print(f"  Terminal: {exe_dir / name}")


def main() -> int:
    parser = argparse.ArgumentParser(description="CareerCraft Agent Build Script")
    parser.add_argument("--native", action="store_true", help="Build native PySide6 version (default builds WebView version)")
    args = parser.parse_args()
    build(native=args.native)
    return 0


if __name__ == "__main__":
    sys.exit(main())
