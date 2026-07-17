"""
CareerCraft Agent — PySide6 主窗口

应用主入口，提供左侧导航栏、右侧内容区域、全局异常捕获、状态栏。
"""

from __future__ import annotations

import sys
import traceback
from typing import List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from src.config.settings import get_settings
from src.ui.pages import ExperiencePage, JobMatchPage, PersonaPage, ResumePage


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
        self.setMinimumSize(1280, 840)

        # 中央控件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 左侧导航边栏
        sidebar = self._build_sidebar()
        main_layout.addWidget(sidebar)

        # 右侧内容区域
        content_area = QWidget()
        content_layout = QVBoxLayout(content_area)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # 顶部标题栏
        header = self._build_header()
        content_layout.addWidget(header)

        # 栈式切换区域
        self.stack = QStackedWidget()
        content_layout.addWidget(self.stack, 1)

        main_layout.addWidget(content_area, 1)

        # 初始化各页面
        self._init_pages()

        # 状态栏
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("就绪")

        # 状态信号连接
        self.status_message.connect(self._on_status_message)

    def _build_sidebar(self) -> QWidget:
        """构建左侧导航边栏"""
        sidebar = QWidget()
        sidebar.setFixedWidth(200)
        sidebar.setStyleSheet(
            "QWidget { background-color: #2c3e50; }"
            "QPushButton {"
            "  text-align: left;"
            "  padding: 12px 16px;"
            "  border: none;"
            "  color: #ecf0f1;"
            "  font-size: 14px;"
            "  background-color: transparent;"
            "}"
            "QPushButton:hover { background-color: #34495e; }"
            "QPushButton:checked { background-color: #3498db; font-weight: bold; }"
        )

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 16, 0, 16)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # 应用名称
        lbl_brand = QLabel("CareerCraft")
        lbl_brand.setStyleSheet("color: #ecf0f1; font-size: 18px; font-weight: bold; padding: 0 16px;")
        layout.addWidget(lbl_brand)

        lbl_version = QLabel(f"v{self.settings.app_version}")
        lbl_version.setStyleSheet("color: #95a5a6; font-size: 11px; padding: 0 16px 16px 16px;")
        layout.addWidget(lbl_version)

        # 导航按钮
        self.nav_buttons: List[QPushButton] = []
        nav_items = [
            ("欢迎", 0),
            ("经历库", 1),
            ("角色档案", 2),
            ("简历生成", 3),
            ("岗位匹配", 4),
            ("设置", 5),
        ]

        for text, index in nav_items:
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.clicked.connect(lambda _checked, idx=index: self.show_page(idx))
            layout.addWidget(btn)
            self.nav_buttons.append(btn)

        layout.addStretch()
        return sidebar

    def _build_header(self) -> QWidget:
        """构建顶部标题栏"""
        header = QWidget()
        header.setFixedHeight(48)
        header.setStyleSheet("background-color: #ecf0f1; border-bottom: 1px solid #bdc3c7;")
        layout = QHBoxLayout(header)
        layout.setContentsMargins(16, 0, 16, 0)

        self.lbl_header = QLabel("欢迎")
        self.lbl_header.setStyleSheet("font-size: 16px; font-weight: bold; color: #2c3e50;")
        layout.addWidget(self.lbl_header)
        layout.addStretch()
        return header

    def _init_pages(self) -> None:
        """初始化各业务页面"""
        self.page_welcome = self._create_placeholder_page(
            "欢迎", "CareerCraft Agent — 角色档案驱动的职业智能体"
        )
        self.page_experiences = ExperiencePage()
        self.page_personas = PersonaPage()
        self.page_resume = ResumePage()
        self.page_jobs = JobMatchPage()
        self.page_settings = self._create_placeholder_page("设置", "应用配置")

        self.stack.addWidget(self.page_welcome)
        self.stack.addWidget(self.page_experiences)
        self.stack.addWidget(self.page_personas)
        self.stack.addWidget(self.page_resume)
        self.stack.addWidget(self.page_jobs)
        self.stack.addWidget(self.page_settings)

        # 默认显示欢迎页
        self.show_page(0)

    def _create_placeholder_page(self, title: str, subtitle: str) -> QWidget:
        """创建占位页面"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("font-size: 24px; font-weight: bold; color: #2c3e50;")
        layout.addWidget(lbl_title, alignment=Qt.AlignmentFlag.AlignCenter)

        lbl_sub = QLabel(subtitle)
        lbl_sub.setStyleSheet("font-size: 14px; color: #7f8c8d;")
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

        # 更新导航按钮状态
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)

        # 更新顶部标题
        titles = ["欢迎", "经历库", "角色档案", "简历生成", "岗位匹配", "设置"]
        if 0 <= index < len(titles):
            self.lbl_header.setText(titles[index])


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
