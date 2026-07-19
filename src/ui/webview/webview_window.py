"""
CareerCraft Agent — WebView 主窗口

PySide6 QWebEngineView 容器，加载本地 HTML 原型，
注入 QWebChannel 桥接以实现 Python ↔ JS 通信。
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

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
        # 配置 WebEngine 设置
        settings = self.web_view.settings()
        try:
            settings.setAttribute(
                QWebEngineSettings.WebAttribute.DeveloperExtrasEnabled, True
            )
        except (AttributeError, TypeError):
            pass
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.LocalStorageEnabled, True
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.JavascriptEnabled, True
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.AllowRunningInsecureContent, True
        )

        # 创建并注册 QWebChannel + Bridge
        self.bridge = CareerBridge(self)
        self.channel = QWebChannel(self.web_view.page())
        self.channel.registerObject("pybridge", self.bridge)
        self.web_view.page().setWebChannel(self.channel)

        # 页面加载完成后注入 qwebchannel.js 并初始化 bridge
        self.web_view.loadFinished.connect(self._on_page_loaded)

        # 加载本地 HTML 原型
        html_path = self._resolve_html_path()
        self.web_view.load(QUrl.fromLocalFile(html_path))

    def _resolve_html_path(self) -> str:
        """Resolve HTML file absolute path in dev, onedir, and onefile bundles."""
        candidates: List[Path] = []

        # PyInstaller bundled environment
        bundle_root = getattr(sys, "_MEIPASS", None)
        if bundle_root:
            candidates.append(Path(bundle_root) / "prototype" / "ui-prototype.html")

        executable_dir = Path(sys.executable).resolve().parent
        source_root = Path(__file__).resolve().parents[3]
        candidates.extend(
            [
                source_root / "prototype" / "ui-prototype.html",
                executable_dir / "prototype" / "ui-prototype.html",
                executable_dir / "_internal" / "prototype" / "ui-prototype.html",
                Path.cwd() / "prototype" / "ui-prototype.html",
            ]
        )

        for path in candidates:
            if path.is_file():
                return str(path)
        # Fallback to first candidate (let WebEngine report the error)
        return str(candidates[0])

    def _get_qwebchannel_js(self) -> str:
        """Read qwebchannel.js content from bundled or source location."""
        candidates: List[Path] = []
        bundle_root = getattr(sys, "_MEIPASS", None)
        if bundle_root:
            candidates.append(Path(bundle_root) / "prototype" / "qwebchannel.js")
        source_root = Path(__file__).resolve().parents[3]
        candidates.extend([
            source_root / "prototype" / "qwebchannel.js",
            Path.cwd() / "prototype" / "qwebchannel.js",
        ])
        for path in candidates:
            if path.is_file():
                return path.read_text(encoding="utf-8")
        return ""

    def _on_page_loaded(self, ok: bool) -> None:
        """Inject qwebchannel.js and initialize bridge after page load."""
        if not ok:
            logger.warning("Page load failed")
            return
        js_code = self._get_qwebchannel_js()
        if js_code:
            self.web_view.page().runJavaScript(js_code)
            self.web_view.page().runJavaScript("initBridge();")
            logger.info("QWebChannel injected and bridge initialized")
        else:
            logger.error("qwebchannel.js not found")

    def keyPressEvent(self, event) -> None:
        """F12 打开 DevTools"""
        from PySide6.QtCore import Qt
        if event.key() == Qt.Key.Key_F12:
            self.web_view.page().setDevToolsPage(QWebEnginePage(self.web_view))
            self.web_view.triggerPageAction(QWebEngineView.WebAction.InspectElement)
        else:
            super().keyPressEvent(event)
