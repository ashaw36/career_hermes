"""
CareerCraft Agent — GUI 页面基类

抽取各业务页面共享的通用工具方法，减少重复代码。
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from PySide6.QtWidgets import QMessageBox, QWidget

logger = logging.getLogger(__name__)


class BasePage(QWidget):
    """业务页面基类"""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

    def _show_task_error(self, title: str) -> Any:
        """返回一个通用的异步任务错误处理闭包。"""

        def _handler(exc: Exception) -> None:
            logger.error("%s: %s", title, exc)
            QMessageBox.critical(self, title, str(exc))

        return _handler
