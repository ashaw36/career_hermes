"""
CareerCraft Agent - PyInstaller Build Script

Supports two entry points:
  - WebView (default): python build.py
  - Native:            python build.py --native

Output:
  - onefile (default): dist/CareerCraftAgent.exe
  - onedir:            dist/CareerCraftAgent/CareerCraftAgent.exe
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Sequence, Tuple


APP_NAME = "CareerCraftAgent"


def get_project_root() -> Path:
    return Path(__file__).parent.resolve()


def detect_separator() -> str:
    """PyInstaller --add-data separator: Windows uses ;, Linux/macOS uses :"""
    return ";" if sys.platform == "win32" else ":"


def run_tests(project_root: Path) -> None:
    """Run the test suite before packaging."""
    cmd = [sys.executable, "-m", "pytest", "tests/", "-q"]
    print("=" * 60)
    print("Pre-build check: pytest tests/ -q")
    print("=" * 60)
    result = subprocess.run(cmd, cwd=project_root)
    if result.returncode != 0:
        print("[ERROR] Tests failed; aborting build.")
        sys.exit(result.returncode)


def ensure_pyinstaller() -> None:
    """Fail early if PyInstaller is not installed."""
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("Error: PyInstaller not installed")
        print("Run: pip install pyinstaller")
        sys.exit(1)


def make_config_placeholders(project_root: Path) -> Path:
    """Create non-secret config placeholders for bundling when local files are absent."""
    placeholder_dir = project_root / "build" / "pyinstaller_placeholders"
    placeholder_dir.mkdir(parents=True, exist_ok=True)

    env_placeholder = placeholder_dir / ".env"
    config_placeholder = placeholder_dir / "config.yaml"

    env_placeholder.write_text(
        "# CareerCraft Agent environment placeholder.\n"
        "# Runtime settings are loaded from environment variables or ~/.careercraft/config.yaml.\n",
        encoding="utf-8",
    )
    config_placeholder.write_text(
        "# CareerCraft Agent config placeholder.\n"
        "# The app creates ~/.careercraft/config.yaml on first run.\n",
        encoding="utf-8",
    )
    return placeholder_dir


def add_data_args(
    cmd: List[str],
    sep: str,
    data_files: Sequence[Tuple[Path, str]],
) -> None:
    """Append existing PyInstaller --add-data entries."""
    for src_path, dst in data_files:
        if src_path.exists():
            cmd.extend(["--add-data", f"{src_path}{sep}{dst}"])
        else:
            print(f"[WARN] Data path not found, skipped: {src_path}")


def build(native: bool = False, onefile: bool = True, skip_tests: bool = False) -> None:
    """Build the application."""
    project_root = get_project_root()
    dist_dir = project_root / "dist"
    build_dir = project_root / "build"
    sep = detect_separator()

    if not skip_tests:
        run_tests(project_root)

    # Clean old builds
    for d in (build_dir, dist_dir):
        if d.exists():
            print(f"Clean: {d}")
            shutil.rmtree(d)

    ensure_pyinstaller()

    entry = "src/main.py" if native else "src/main_webview.py"
    name = APP_NAME
    bundle_mode = "--onefile" if onefile else "--onedir"
    placeholder_dir = make_config_placeholders(project_root)

    # Base command
    cmd: List[str] = [
        sys.executable, "-m", "PyInstaller",
        "--name", name,
        bundle_mode,
        "--windowed",
        "--clean",
        "--noconfirm",
    ]

    # Data files (HTML prototype + templates + assets)
    data_files = [
        (project_root / "prototype", "prototype"),
        (project_root / "src" / "ui" / "templates", "src/ui/templates"),
        (project_root / ".env" if (project_root / ".env").exists() else placeholder_dir / ".env", "."),
        (
            project_root / "config.yaml"
            if (project_root / "config.yaml").exists()
            else placeholder_dir / "config.yaml",
            ".",
        ),
    ]
    add_data_args(cmd, sep, data_files)

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
        "pydantic_settings",
        "yaml",
        "markdown",
        "PySide6",
        "PySide6.QtWebEngineWidgets",
        "PySide6.QtWebChannel",
        "PySide6.QtWebEngineCore",
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
        "fpdf",
        "cryptography",
    ]
    if native:
        hidden_imports.append("qasync")

    for mod in hidden_imports:
        cmd.extend(["--hidden-import", mod])

    # Collect all PySide6 (ensure QtWebEngine process and resources are bundled)
    cmd.extend(["--collect-all", "PySide6"])

    # Entry point
    cmd.append(str(project_root / entry))

    print("=" * 60)
    print(f"Building: {name}")
    print(f"Entry: {entry}")
    print(f"Mode: {bundle_mode[2:]}")
    print(f"Platform: {sys.platform}")
    print("=" * 60)
    print(f"Command:\n{' '.join(cmd)}")
    print()

    result = subprocess.run(cmd, cwd=project_root)
    if result.returncode != 0:
        print("[ERROR] Build failed!")
        sys.exit(1)

    exe_name = name + ".exe" if sys.platform == "win32" else name
    if onefile:
        exe_path = dist_dir / exe_name
        if not exe_path.exists():
            print(f"[WARN] Output executable not found: {exe_path}")
            sys.exit(1)
        output_path = exe_path
    else:
        exe_dir = dist_dir / name
        exe_path = exe_dir / exe_name
        if not exe_dir.exists():
            print(f"[WARN] Output dir not found: {exe_dir}")
            sys.exit(1)
        if not exe_path.exists():
            print(f"[WARN] Output executable not found: {exe_path}")
            sys.exit(1)
        output_path = exe_dir

    print()
    print("[OK] Build completed!")
    print(f"Output: {output_path}")

    # List key files
    print("\nKey files check:")
    size_mb = exe_path.stat().st_size / (1024 * 1024)
    print(f"  [OK] {exe_name} ({size_mb:.1f} MB)")
    print("  [OK] prototype/ui-prototype.html scheduled for bundle")
    print("  [OK] prototype/qwebchannel.js scheduled for bundle")
    print("  [OK] src/ui/templates/ scheduled for bundle")
    print("  [OK] config.yaml/.env placeholders scheduled for bundle")

    if not onefile:
        bundle_root = exe_path.parent / "_internal"
        if not bundle_root.exists():
            bundle_root = exe_path.parent
        prototype_dir = bundle_root / "prototype"
        templates_dir = bundle_root / "src" / "ui" / "templates"
        if prototype_dir.exists():
            print(f"  [OK] prototype/ included ({len(list(prototype_dir.iterdir()))} files)")
        else:
            print("  [WARN] prototype/ not found in output")
        if templates_dir.exists():
            print("  [OK] src/ui/templates/ included")
        else:
            print("  [WARN] src/ui/templates/ not found in output")
    else:
        print("  [INFO] onefile resources are embedded and extracted to sys._MEIPASS at runtime")

    print("\nLaunch:")
    if sys.platform == "win32":
        print(f"  Double-click: {exe_path}")
    else:
        print(f"  Terminal: {exe_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="CareerCraft Agent Build Script")
    parser.add_argument("--native", action="store_true", help="Build native PySide6 version (default builds WebView version)")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--onefile", action="store_true", help="Build a single executable file (default)")
    mode.add_argument("--onedir", action="store_true", help="Build an executable directory")
    parser.add_argument("--skip-tests", action="store_true", help="Skip pytest pre-build check")
    args = parser.parse_args()
    build(native=args.native, onefile=not args.onedir, skip_tests=args.skip_tests)
    return 0


if __name__ == "__main__":
    sys.exit(main())
