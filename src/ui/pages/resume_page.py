"""
CareerCraft Agent — 简历预览页面

顶部角色/模板选择 + 生成，中部 Markdown 预览，底部导出。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, List, Optional, Set

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
from src.ui.async_tasks import start_async_task


class ResumePage(QWidget):
    """简历预览页面"""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.persona_engine = PersonaEngine()
        self._personas: List[Persona] = []
        self._async_tasks: Set[Any] = set()

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
        self.combo_template.addItems(["modern", "classic", "minimal", "tech", "外企"])
        self.combo_template.setMinimumWidth(120)
        control_bar.addWidget(self.combo_template)

        self.btn_generate = QPushButton("生成简历")
        self.btn_generate.setStyleSheet(
            "QPushButton { padding: 6px 18px; font-weight: bold; }"
        )
        control_bar.addWidget(self.btn_generate)

        control_bar.addStretch()
        layout.addLayout(control_bar)

        self.status_label = QLabel()
        self.status_label.setStyleSheet("color: #666;")
        layout.addWidget(self.status_label)

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

    def _load_personas(self) -> None:
        """加载角色下拉列表。"""
        self.combo_persona.clear()
        start_async_task(
            self,
            self.status_label,
            "正在加载角色...",
            self.persona_engine.list_by_user,
            self._populate_personas,
            self._show_task_error("加载角色失败"),
            [self.combo_persona, self.btn_generate, self.btn_export, self.btn_export_pdf],
        )

    def _populate_personas(self, personas: List[Persona]) -> None:
        self.combo_persona.clear()
        self._personas = personas
        if not self._personas:
            self.combo_persona.addItem("暂无角色，请先创建")
            self.combo_persona.setEnabled(False)
            self.btn_generate.setEnabled(False)
            return
        self.combo_persona.setEnabled(True)
        self.btn_generate.setEnabled(True)
        for p in self._personas:
            self.combo_persona.addItem(p.name, p.id)

    def _show_task_error(self, title: str) -> Any:
        def _handler(exc: Exception) -> None:
            QMessageBox.critical(self, title, str(exc))

        return _handler

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
            async def generate() -> str:
                builder = ResumeBuilder(persona_id=persona_id)
                await builder.prepare()
                return await builder.render(template_name=template_name)

            start_async_task(
                self,
                self.status_label,
                "正在生成简历...",
                generate,
                lambda md_content: self.preview_edit.setPlainText(md_content),
                self._show_task_error("生成失败"),
                [self.btn_generate, self.btn_export, self.btn_export_pdf, self.combo_persona, self.combo_template],
            )
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

        async def write_markdown() -> str:
            path = Path(filepath)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            return filepath

        start_async_task(
            self,
            self.status_label,
            "正在导出 Markdown...",
            write_markdown,
            lambda saved_path: QMessageBox.information(self, "成功", f"已导出到：\n{saved_path}"),
            self._show_task_error("导出失败"),
            [self.btn_export, self.btn_export_pdf, self.btn_generate],
        )

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

            async def export_pdf() -> str:
                # 1. 先用 ResumeBuilder 筛选角色适配的经历
                builder = ResumeBuilder(persona_id=persona_id)
                await builder.prepare()
                # 从 builder 中提取 Experience 对象（已按 Fit Score 排序和过滤）
                filtered_experiences = [rew.experience for rew in builder._experiences]

                # 2. 加载角色
                persona = await self.persona_engine.get_by_id(persona_id)
                if not persona:
                    raise RuntimeError("无法加载角色信息。")

                # 3. 导出 PDF
                exporter = PDFExporter()
                await exporter.save_resume(persona, filtered_experiences, Path(filepath))
                return filepath

            start_async_task(
                self,
                self.status_label,
                "正在导出 PDF...",
                export_pdf,
                lambda saved_path: QMessageBox.information(self, "成功", f"PDF 已导出到：\n{saved_path}"),
                self._show_task_error("导出失败"),
                [self.btn_export_pdf, self.btn_export, self.btn_generate],
            )
        except PDFExporterError as exc:
            QMessageBox.critical(self, "导出失败", str(exc))
        except Exception as exc:
            QMessageBox.critical(self, "导出失败", f"生成 PDF 时出错：\n{exc}")
