"""
CareerCraft Agent — 应用主入口

启动流程：初始化配置 → 初始化数据库 → 启动 GUI。
"""

from __future__ import annotations

import asyncio
import sys

import qasync
from PySide6.QtWidgets import QApplication

from src.config.settings import create_default_config, get_settings
from src.models.database import init_db
from src.ui.main_window import MainWindow


def main() -> int:
    """应用主入口，使用 qasync 统一 Qt 与 asyncio 事件循环。"""
    app = QApplication(sys.argv)
    app.setApplicationName("CareerCraft Agent")
    app.setApplicationVersion("0.1.0")

    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    async def async_main() -> None:
        settings = get_settings()
        print(f"[{settings.app_name} v{settings.app_version}] 启动中...")
        await init_db()
        print("数据库初始化完成")
        window = MainWindow()
        window.show()
        # 等待应用程序退出信号，保持事件循环运行
        future = asyncio.Future()
        app.aboutToQuit.connect(future.set_result)
        await future

    with loop:
        loop.run_until_complete(async_main())
        return 0


if __name__ == "__main__":
    sys.exit(main())
