"""
CareerCraft Agent — WebView 主窗口

PySide6 QWebEngineView 容器，加载本地 HTML 原型，
注入 QWebChannel 桥接以实现 Python ↔ JS 通信。
"""

from __future__ import annotations

import os
import sys
from typing import Optional

from PySide6.QtCore import QUrl
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QMainWindow

from src.ui.webview.bridge import CareerBridge


class CareerWebWindow(QMainWindow):
    """
    CareerCraft Agent WebView 主窗口

    特性：
    - 加载本地 HTML 原型 (prototype/ui-prototype.html)
    - 注入 QWebChannel 供 JS 调用 Python API
    - F12 开启 DevTools
    - 窗口大小 1280x800，深色标题栏
    """

    def __init__(self, parent: Optional[QMainWindow] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("CareerCraft Agent")
        self.resize(1280, 800)

        # 创建 WebEngineView
        self.web_view = QWebEngineView(self)
        self.setCentralWidget(self.web_view)

        # 配置 WebEngine 设置
        settings = self.web_view.settings()
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.DeveloperExtrasEnabled, True
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.LocalStorageEnabled, True
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.JavascriptEnabled, True
        )

        # 创建并注册 QWebChannel + Bridge
        self.bridge = CareerBridge(self)
        self.channel = QWebChannel(self.web_view.page())
        self.channel.registerObject("pybridge", self.bridge)
        self.web_view.page().setWebChannel(self.channel)

        # 加载本地 HTML 原型
        html_path = self._resolve_html_path()
        self.web_view.load(QUrl.fromLocalFile(html_path))

    def _resolve_html_path(self) -> str:
        """Resolve HTML file absolute path (dev vs PyInstaller bundle)"""
        candidates: list[str] = []

        # PyInstaller bundled environment
        if hasattr(sys, "_MEIPASS"):
            candidates.append(
                os.path.join(sys._MEIPASS, "prototype", "ui-prototype.html")
            )

        candidates.extend([
            # Dev: relative to this file (project root)
            os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "..", "..", "prototype", "ui-prototype.html")
            ),
            # Legacy bundle: sibling to executable
            os.path.join(os.path.dirname(sys.executable), "prototype", "ui-prototype.html"),
            # Current working dir
            os.path.abspath("prototype/ui-prototype.html"),
        ])

        for path in candidates:
            if os.path.isfile(path):
                return path
        # Fallback to first candidate (let WebEngine report the error)
        return candidates[0]

    def keyPressEvent(self, event) -> None:
        """F12 打开 DevTools"""
        from PySide6.QtCore import Qt
        if event.key() == Qt.Key.Key_F12:
            self.web_view.page().setDevToolsPage(QWebEnginePage(self.web_view))
            self.web_view.triggerPageAction(QWebEngineView.WebAction.InspectElement)
        else:
            super().keyPressEvent(event)
