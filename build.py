"""
CareerCraft Agent — PyInstaller 打包脚本

使用流程：
    python build.py

输出：dist/CareerCraftAgent/
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path
import os


def build() -> None:
    """打包应用"""
    project_root = Path(__file__).parent
    dist_dir = project_root / "dist"
    build_dir = project_root / "build"

    # 清理旧构建
    if build_dir.exists():
        shutil.rmtree(build_dir)
    if dist_dir.exists():
        shutil.rmtree(dist_dir)

    # 检查 PyInstaller
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("错误: 未安装 PyInstaller")
        print("请运行: pip install pyinstaller")
        sys.exit(1)

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", "CareerCraftAgent",
        "--onedir",
        "--windowed",
        "--clean",
        "--noconfirm",
        "--add-data", f"src/templates{os.pathsep}src/templates",
        "--add-data", f"src/assets{os.pathsep}src/assets",
        "--hidden-import", "sqlalchemy.ext.asyncio",
        "--hidden-import", "jinja2",
        "--hidden-import", "keyring",
        "--hidden-import", "httpx",
        "--hidden-import", "pydantic",
        "--hidden-import", "PySide6",
        "--collect-all", "PySide6",
        str(project_root / "src" / "main.py"),
    ]

    print("开始打包...")
    print(f"命令: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=project_root)
    if result.returncode != 0:
        print("打包失败！")
        sys.exit(1)

    print()
    print("✅ 打包完成！")
    print(f"输出目录: {dist_dir / 'CareerCraftAgent'}")


if __name__ == "__main__":
    build()
