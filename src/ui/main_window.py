"""
CareerCraft Agent — PySide6 主窗口

应用主入口，提供导航、全局异常捕获、主题切换。
"""

from __future__ import annotations

import sys
import traceback
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from src.config.settings import get_settings


class MainWindow(QMainWindow):
    """主窗口类"""

    # 用于后台线程向主线程通知状态变化
    status_message = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.settings = get_settings()
        self._init_ui()
        self._setup_global_exception_handler()

    def _init_ui(self) -> None:
        """初始化界面"""
        self.setWindowTitle(self.settings.app_name)
        self.setMinimumSize(1200, 800)

        # 中央控件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 导航栏
        nav_bar = self._build_nav_bar()
        layout.addWidget(nav_bar)

        # 内容区域（栈式切换）
        self.stack = QStackedWidget()
        layout.addWidget(self.stack, 1)

        # 初始化各页面
        self._init_pages()

        # 状态栏
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("就绪")

        # 状态信号连接
        self.status_message.connect(self._on_status_message)

    def _build_nav_bar(self) -> QWidget:
        """构建顶部导航栏"""
        nav = QWidget()
        nav.setFixedHeight(48)
        nav_layout = QVBoxLayout(nav)
        nav_layout.setContentsMargins(12, 0, 12, 0)
        nav_layout.setSpacing(8)

        # 标题
        title = QLabel("CareerCraft Agent")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        nav_layout.addWidget(title)

        return nav

    def _init_pages(self) -> None:
        """初始化各业务页面"""
        # 占位页面，后续由具体页面类替换
        self.page_welcome = self._create_placeholder_page("欢迎", "CareerCraft Agent — 角色档案驱动的职业智能体")
        self.page_experiences = self._create_placeholder_page("经历库", "管理你的职业经历")
        self.page_personas = self._create_placeholder_page("角色档案", "配置多角色侧重")
        self.page_resume = self._create_placeholder_page("简历生成", "一键生成定制化简历")
        self.page_jobs = self._create_placeholder_page("岗位匹配", "粘贴 JD 分析匹配度")
        self.page_settings = self._create_placeholder_page("设置", "应用配置")

        self.stack.addWidget(self.page_welcome)
        self.stack.addWidget(self.page_experiences)
        self.stack.addWidget(self.page_personas)
        self.stack.addWidget(self.page_resume)
        self.stack.addWidget(self.page_jobs)
        self.stack.addWidget(self.page_settings)

    def _create_placeholder_page(self, title: str, subtitle: str) -> QWidget:
        """创建占位页面"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(lbl_title, alignment=Qt.AlignmentFlag.AlignCenter)

        lbl_sub = QLabel(subtitle)
        lbl_sub.setStyleSheet("font-size: 14px; color: gray;")
        layout.addWidget(lbl_sub, alignment=Qt.AlignmentFlag.AlignCenter)

        return page

    def _setup_global_exception_handler(self) -> None:
        """设置全局异常处理器"""
        def handle_exception(exc_type, exc_value, exc_traceback):
            if issubclass(exc_type, KeyboardInterrupt):
                sys.__excepthook__(exc_type, exc_value, exc_traceback)
                return

            error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
            print(f"[Unhandled Exception]\n{error_msg}")

            QMessageBox.critical(
                self,
                "应用错误",
                f"发生未预期错误：\n{exc_value}\n\n详情已记录到日志。",
            )

        sys.excepthook = handle_exception

    def _on_status_message(self, message: str) -> None:
        """状态栏更新"""
        self.status_bar.showMessage(message, 5000)

    def show_page(self, index: int) -> None:
        """切换页面"""
        self.stack.setCurrentIndex(index)


def run_app() -> int:
    """应用入口"""
    app = QApplication(sys.argv)
    app.setApplicationName("CareerCraft Agent")
    app.setApplicationVersion("0.1.0")

    # 高 DPI 适配
    app.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(run_app())
