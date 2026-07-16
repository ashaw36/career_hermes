"""
CareerCraft Agent — 应用主入口

启动流程：初始化配置 → 初始化数据库 → 启动 GUI。
"""

from __future__ import annotations

import asyncio
import sys

from src.config.settings import create_default_config, get_settings
from src.models.database import init_db
from src.ui.main_window import run_app


async def async_main() -> int:
    """异步初始化主函数"""
    # 确保配置文件存在
    settings = get_settings()
    print(f"[{settings.app_name} v{settings.app_version}] 启动中...")

    # 初始化数据库
    await init_db()
    print("数据库初始化完成")

    # 启动 GUI（阻塞式，在主线程）
    return run_app()


def main() -> int:
    """同步入口，包装异步初始化"""
    try:
        return asyncio.run(async_main())
    except KeyboardInterrupt:
        print("\n用户中断，应用退出")
        return 0


if __name__ == "__main__":
    sys.exit(main())
