"""
CareerCraft Agent — 简历预览页面

顶部角色/模板选择 + 生成，中部 Markdown 预览，底部导出。
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, List, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.config.settings import get_settings
from src.models.entities import Persona
from src.services.persona_engine import PersonaEngine
from src.services.resume_builder import ResumeBuilder


class ResumePage(QWidget):
    """简历预览页面"""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.persona_engine = PersonaEngine()
        self._personas: List[Persona] = []

        self._init_ui()
        self._load_personas()

    def _init_ui(self) -> None:
        """初始化界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # 顶部控制栏
        control_bar = QHBoxLayout()
        control_bar.setSpacing(12)

        control_bar.addWidget(QLabel("角色："))
        self.combo_persona = QComboBox()
        self.combo_persona.setMinimumWidth(180)
        control_bar.addWidget(self.combo_persona)

        control_bar.addWidget(QLabel("模板："))
        self.combo_template = QComboBox()
        self.combo_template.addItems(["modern"])
        self.combo_template.setMinimumWidth(120)
        control_bar.addWidget(self.combo_template)

        self.btn_generate = QPushButton("生成简历")
        self.btn_generate.setStyleSheet(
            "QPushButton { padding: 6px 18px; font-weight: bold; }"
        )
        control_bar.addWidget(self.btn_generate)

        control_bar.addStretch()
        layout.addLayout(control_bar)

        # 预览区
        self.preview_edit = QTextEdit()
        self.preview_edit.setReadOnly(True)
        self.preview_edit.setPlaceholderText("点击“生成简历”查看预览...")
        self.preview_edit.setStyleSheet(
            "QTextEdit { font-family: 'Consolas', 'Courier New', monospace; font-size: 13px; }"
        )
        layout.addWidget(self.preview_edit, 1)

        # 底部操作栏
        bottom_bar = QHBoxLayout()
        bottom_bar.addStretch()

        self.btn_export = QPushButton("导出 Markdown")
        self.btn_export.setStyleSheet(
            "QPushButton { padding: 6px 18px; }"
        )
        bottom_bar.addWidget(self.btn_export)

        self.btn_export_pdf = QPushButton("导出 PDF")
        self.btn_export_pdf.setStyleSheet(
            "QPushButton { background-color: #e74c3c; color: white; padding: 6px 18px; }"
        )
        bottom_bar.addWidget(self.btn_export_pdf)

        layout.addLayout(bottom_bar)

        # 信号连接
        self.btn_generate.clicked.connect(self._on_generate)
        self.btn_export.clicked.connect(self._on_export)
        self.btn_export_pdf.clicked.connect(self._on_export_pdf)

    @staticmethod
    def _run_async(coro: Any) -> Any:
        """在独立事件循环中运行异步协程。"""
        try:
            return asyncio.run(coro)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(coro)
            finally:
                loop.close()

    def _load_personas(self) -> None:
        """加载角色下拉列表。"""
        self.combo_persona.clear()
        self._personas = self._run_async(self.persona_engine.list_by_user())
        if not self._personas:
            self.combo_persona.addItem("暂无角色，请先创建")
            self.combo_persona.setEnabled(False)
            self.btn_generate.setEnabled(False)
            return
        self.combo_persona.setEnabled(True)
        self.btn_generate.setEnabled(True)
        for p in self._personas:
            self.combo_persona.addItem(p.name, p.id)

    def _on_generate(self) -> None:
        """生成简历并预览。"""
        if not self._personas:
            QMessageBox.information(self, "提示", "请先在“角色档案”页面创建角色。")
            return

        persona_id = self.combo_persona.currentData()
        template_name = self.combo_template.currentText()
        if not persona_id:
            QMessageBox.warning(self, "校验失败", "请选择角色。")
            return

        try:
            builder = ResumeBuilder(persona_id=persona_id)
            self._run_async(builder.prepare())
            md_content = self._run_async(builder.render(template_name=template_name))
            self.preview_edit.setPlainText(md_content)
        except Exception as exc:
            QMessageBox.critical(self, "生成失败", f"生成简历时出错：\n{exc}")

    def _on_export(self) -> None:
        """导出 Markdown 文件。"""
        content = self.preview_edit.toPlainText().strip()
        if not content:
            QMessageBox.information(self, "提示", "请先生成简历内容。")
            return

        settings = get_settings()
        default_dir = settings.export_dir
        default_name = f"简历_{self.combo_persona.currentText()}.md"
        filepath, _filter = QFileDialog.getSaveFileName(
            self,
            "导出简历",
            str(Path(default_dir) / default_name),
            "Markdown 文件 (*.md)",
        )
        if not filepath:
            return

        try:
            path = Path(filepath)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            QMessageBox.information(self, "成功", f"已导出到：\n{filepath}")
        except Exception as exc:
            QMessageBox.critical(self, "导出失败", f"写入文件失败：\n{exc}")

    def _on_export_pdf(self) -> None:
        """导出 PDF 文件。"""
        persona_id = self.combo_persona.currentData()
        if not persona_id:
            QMessageBox.warning(self, "校验失败", "请选择角色。")
            return

        try:
            from src.services.pdf_exporter import PDFExporter, PDFExporterError, FPDF_AVAILABLE

            if not FPDF_AVAILABLE:
                QMessageBox.warning(
                    self, "缺少依赖",
                    "PDF 导出需要 fpdf2 库。\n\n请运行：\npip install fpdf2"
                )
                return

            settings = get_settings()
            default_dir = settings.export_dir
            default_name = f"简历_{self.combo_persona.currentText()}.pdf"
            filepath, _filter = QFileDialog.getSaveFileName(
                self,
                "导出 PDF 简历",
                str(Path(default_dir) / default_name),
                "PDF 文件 (*.pdf)",
            )
            if not filepath:
                return

            # 加载角色和经历
            persona = self._run_async(
                self.persona_engine.get_by_id(persona_id)
            )
            if not persona:
                QMessageBox.warning(self, "错误", "无法加载角色信息。")
                return

            from src.services.experience_manager import ExperienceManager
            exp_mgr = ExperienceManager()
            experiences = self._run_async(
                exp_mgr.list_by_user(status_filter="confirmed")
            )

            exporter = PDFExporter()
            self._run_async(
                exporter.save_resume(persona, experiences, Path(filepath))
            )
            QMessageBox.information(self, "成功", f"PDF 已导出到：\n{filepath}")
        except PDFExporterError as exc:
            QMessageBox.critical(self, "导出失败", str(exc))
        except Exception as exc:
            QMessageBox.critical(self, "导出失败", f"生成 PDF 时出错：\n{exc}")
