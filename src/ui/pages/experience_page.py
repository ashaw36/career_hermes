"""
CareerCraft Agent — 经历管理页面

左侧经历列表，右侧表单录入/编辑。支持新增、编辑、软删除。
"""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDateEdit,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.models.entities import Experience
from src.services.experience_manager import ExperienceManager
from src.ui.async_tasks import start_async_task

logger = logging.getLogger(__name__)


class ExperiencePage(QWidget):
    """经历管理页面"""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.manager = ExperienceManager()
        self._current_exp_id: Optional[str] = None
        self._experiences: List[Experience] = []
        self._async_tasks: set[Any] = set()

        self._init_ui()
        self._load_data()

    def _init_ui(self) -> None:
        """初始化界面"""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)

        # 左侧：列表区
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        # 工具栏
        toolbar = QHBoxLayout()
        self.btn_new = QPushButton("新增经历")
        self.btn_new.setToolTip("创建一条新的经历")
        self.btn_delete = QPushButton("删除")
        self.btn_delete.setToolTip("软删除选中经历（移至 archived）")
        self.btn_refresh = QPushButton("刷新")
        self.btn_refresh.setToolTip("重新加载经历列表")
        self.btn_import = QPushButton("批量导入")
        self.btn_import.setToolTip("从 Markdown/文本/JSON 导入经历")
        self.btn_import.setStyleSheet(
            "QPushButton { background-color: #3498db; color: white; }"
        )
        toolbar.addWidget(self.btn_new)
        toolbar.addWidget(self.btn_delete)
        toolbar.addWidget(self.btn_import)
        toolbar.addStretch()
        toolbar.addWidget(self.btn_refresh)
        left_layout.addLayout(toolbar)

        self.status_label = QLabel()
        self.status_label.setStyleSheet("color: #666;")
        left_layout.addWidget(self.status_label)

        # 经历列表
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.list_widget.setSpacing(4)
        left_layout.addWidget(self.list_widget)

        splitter.addWidget(left_panel)

        # 右侧：表单区
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        form_container = QWidget()
        form_layout = QFormLayout(form_container)
        form_layout.setContentsMargins(16, 16, 16, 16)
        form_layout.setSpacing(12)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.edit_title = QLineEdit()
        self.edit_title.setPlaceholderText("例：高级产品经理")
        form_layout.addRow("标题：", self.edit_title)

        self.edit_org = QLineEdit()
        self.edit_org.setPlaceholderText("例：某某科技有限公司")
        form_layout.addRow("公司/组织：", self.edit_org)

        self.combo_type = QComboBox()
        self.combo_type.addItems(["work", "project", "education", "certification"])
        form_layout.addRow("类型：", self.combo_type)

        date_layout = QHBoxLayout()
        self.date_start = QDateEdit()
        self.date_start.setCalendarPopup(True)
        self.date_start.setDisplayFormat("yyyy-MM-dd")
        self.date_start.setDate(date.today())
        self.date_end = QDateEdit()
        self.date_end.setCalendarPopup(True)
        self.date_end.setDisplayFormat("yyyy-MM-dd")
        self.date_end.setDate(date.today())
        date_layout.addWidget(QLabel("开始："))
        date_layout.addWidget(self.date_start)
        date_layout.addWidget(QLabel("结束："))
        date_layout.addWidget(self.date_end)
        date_layout.addStretch()
        form_layout.addRow("时间区间：", date_layout)

        self.edit_desc = QTextEdit()
        self.edit_desc.setPlaceholderText("请输入经历描述...")
        self.edit_desc.setMinimumHeight(120)
        form_layout.addRow("描述：", self.edit_desc)

        self.edit_skills = QLineEdit()
        self.edit_skills.setPlaceholderText("多个技能用英文逗号分隔，如：Python, 产品规划, 数据分析")
        form_layout.addRow("技能：", self.edit_skills)

        self.edit_achievements = QTextEdit()
        self.edit_achievements.setPlaceholderText("每行一个成就，支持 Markdown 格式")
        self.edit_achievements.setMinimumHeight(100)
        form_layout.addRow("成就：", self.edit_achievements)

        self.btn_save = QPushButton("保存")
        self.btn_save.setStyleSheet(
            "QPushButton { padding: 8px 24px; font-weight: bold; }"
        )
        form_layout.addRow(self.btn_save)

        scroll.setWidget(form_container)
        splitter.addWidget(scroll)
        splitter.setSizes([360, 640])

        # 信号连接
        self.btn_new.clicked.connect(self._on_new)
        self.btn_delete.clicked.connect(self._on_delete)
        self.btn_import.clicked.connect(self._on_import)
        self.btn_refresh.clicked.connect(self._load_data)
        self.btn_save.clicked.connect(self._on_save)
        self.list_widget.currentItemChanged.connect(self._on_item_changed)

    def _load_data(self) -> None:
        """加载经历列表。"""
        self.list_widget.clear()
        start_async_task(
            self,
            self.status_label,
            "正在加载经历...",
            lambda: self.manager.list_by_user(status_filter="confirmed"),
            lambda exps: self._populate_experiences(exps),
            self._show_task_error("加载失败"),
            [self.btn_refresh, self.btn_save, self.btn_delete, self.btn_import],
        )

    def _populate_experiences(
        self, experiences: List[Experience], selected_id: Optional[str] = None
    ) -> None:
        self.list_widget.clear()
        self._experiences = experiences
        selected_item: Optional[QListWidgetItem] = None
        for exp in self._experiences:
            item = QListWidgetItem(self._format_list_text(exp))
            item.setData(Qt.ItemDataRole.UserRole, exp.id)
            self.list_widget.addItem(item)
            if selected_id and exp.id == selected_id:
                selected_item = item
        if selected_item:
            self.list_widget.setCurrentItem(selected_item)
        else:
            self._clear_form()

    def _show_task_error(self, title: str) -> Any:
        def _handler(exc: Exception) -> None:
            logger.error("%s: %s", title, exc)
            QMessageBox.critical(self, title, str(exc))

        return _handler

    def _set_form(self, exp: Experience) -> None:
        self._current_exp_id = exp.id
        self.edit_title.setText(exp.title)
        self.edit_org.setText(exp.organization or "")
        self.combo_type.setCurrentText(exp.type)
        self.date_start.setDate(exp.start_date or date.today())
        self.date_end.setDate(exp.end_date or date.today())
        self.edit_desc.setPlainText(exp.raw_description)
        skills = ", ".join(exp.skills_demonstrated or [])
        self.edit_skills.setText(skills)
        achievements = "\n".join(exp.structured_achievements or [])
        self.edit_achievements.setPlainText(achievements)

    def _format_list_text(self, exp: Experience) -> str:
        """格式化列表项文本。"""
        org = exp.organization or "未知组织"
        period = self._format_period(exp.start_date, exp.end_date)
        return f"{exp.title}\n{org}  |  {period}"

    @staticmethod
    def _format_period(start: Optional[date], end: Optional[date]) -> str:
        """格式化日期区间。"""
        start_str = start.strftime("%Y.%m") if start else "?"
        end_str = end.strftime("%Y.%m") if end else "至今"
        return f"{start_str} — {end_str}"

    def _on_item_changed(self, current: Optional[QListWidgetItem], _previous: Optional[QListWidgetItem]) -> None:
        """列表项切换时加载详情。"""
        if current is None:
            self._clear_form()
            return
        exp_id = current.data(Qt.ItemDataRole.UserRole)

        def on_success(exp: Optional[Experience]) -> None:
            current_item = self.list_widget.currentItem()
            if current_item is None or current_item.data(Qt.ItemDataRole.UserRole) != exp_id:
                return
            if exp is not None:
                self._set_form(exp)

        start_async_task(
            self,
            self.status_label,
            "正在加载经历详情...",
            lambda: self.manager.get_by_id(exp_id),
            on_success,
            self._show_task_error("加载详情失败"),
            [self.list_widget],
        )

    def _clear_form(self) -> None:
        """清空表单。"""
        self._current_exp_id = None
        self.edit_title.clear()
        self.edit_org.clear()
        self.combo_type.setCurrentIndex(0)
        self.date_start.setDate(date.today())
        self.date_end.setDate(date.today())
        self.edit_desc.clear()
        self.edit_skills.clear()
        self.edit_achievements.clear()

    def _on_new(self) -> None:
        """新增经历：清空表单并聚焦。"""
        self.list_widget.clearSelection()
        self._clear_form()
        self.edit_title.setFocus()

    def _on_delete(self) -> None:
        """软删除当前选中经历。"""
        item = self.list_widget.currentItem()
        if item is None:
            QMessageBox.information(self, "提示", "请先选择要删除的经历。")
            return
        exp_id = item.data(Qt.ItemDataRole.UserRole)
        reply = QMessageBox.question(
            self,
            "确认删除",
            "确定要删除这条经历吗？（将移至已归档）",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        async def delete_and_reload() -> tuple[bool, List[Experience]]:
            ok = await self.manager.delete(exp_id)
            exps = await self.manager.list_by_user(status_filter="confirmed")
            return ok, exps

        def on_success(result: tuple[bool, List[Experience]]) -> None:
            ok, exps = result
            if ok:
                self._populate_experiences(exps)
                QMessageBox.information(self, "成功", "经历已删除。")
            else:
                QMessageBox.warning(self, "失败", "删除经历失败，请检查日志。")

        start_async_task(
            self,
            self.status_label,
            "正在删除经历...",
            delete_and_reload,
            on_success,
            self._show_task_error("删除失败"),
            [self.btn_delete, self.btn_save, self.btn_refresh, self.btn_import],
        )

    def _on_save(self) -> None:
        """保存表单数据。"""
        title = self.edit_title.text().strip()
        if not title:
            QMessageBox.warning(self, "校验失败", "标题为必填项。")
            return

        org = self.edit_org.text().strip() or None
        exp_type = self.combo_type.currentText()
        start_date = self.date_start.date().toPython()
        end_date = self.date_end.date().toPython()
        desc = self.edit_desc.toPlainText().strip()
        skills = [s.strip() for s in self.edit_skills.text().split(",") if s.strip()]
        achievements = [a.strip() for a in self.edit_achievements.toPlainText().splitlines() if a.strip()]

        data: Dict[str, Any] = {
            "title": title,
            "organization": org,
            "type": exp_type,
            "start_date": start_date,
            "end_date": end_date,
            "raw_description": desc,
            "skills_demonstrated": skills or None,
            "structured_achievements": achievements or None,
        }

        try:
            async def save_and_reload() -> tuple[str, str, List[Experience]]:
                action = "updated"
                if self._current_exp_id:
                    exp = await self.manager.update(self._current_exp_id, **data)
                    if not exp:
                        raise RuntimeError("更新经历失败。")
                else:
                    # 新增经历：先创建草稿，然后保存
                    from src.services.experience_manager import ExperienceDraft
                    draft = ExperienceDraft(
                        raw_text=desc,
                        extracted={
                            "title": title,
                            "organization": org,
                            "type": exp_type,
                            "start_date": start_date.isoformat() if start_date else None,
                            "end_date": end_date.isoformat() if end_date else None,
                            "structured_achievements": achievements or None,
                            "skills_demonstrated": skills or None,
                        },
                    )
                    exp = await self.manager.confirm_and_save(draft)
                    action = "created"
                exps = await self.manager.list_by_user(status_filter="confirmed")
                return action, exp.id, exps

            def on_success(result: tuple[str, str, List[Experience]]) -> None:
                action, exp_id, exps = result
                self._current_exp_id = exp_id
                self._populate_experiences(exps, selected_id=exp_id)
                if action == "updated":
                    QMessageBox.information(self, "成功", "经历已更新。")
                else:
                    QMessageBox.information(self, "成功", "经历已创建。")

            start_async_task(
                self,
                self.status_label,
                "正在保存经历...",
                save_and_reload,
                on_success,
                self._show_task_error("保存失败"),
                [self.btn_save, self.btn_delete, self.btn_refresh, self.btn_import],
            )
        except Exception as e:
            logger.error("保存经历失败: %s", e)
            QMessageBox.critical(self, "保存失败", f"保存经历时出现错误：\n{e}")

    def _on_import(self) -> None:
        """打开批量导入对话框。"""
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QTextEdit, QPushButton, QLabel

        dialog = QDialog(self)
        dialog.setWindowTitle("批量导入经历")
        dialog.setMinimumSize(600, 500)
        layout = QVBoxLayout(dialog)

        # 格式说明
        info = QLabel(
            "支持 Markdown、纯文本、JSON 三种格式。\n"
            "Markdown 建议使用 ## 标题分类，### 标题标注经历。\n"
            "JSON 需为对象数组，每个对象含 title, type 等字段。"
        )
        info.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(info)

        # Tab 切换
        tabs = QTabWidget()
        md_edit = QTextEdit()
        md_edit.setPlaceholderText("粘贴 Markdown 格式经历...")
        text_edit = QTextEdit()
        text_edit.setPlaceholderText("粘贴纯文本格式经历...")
        json_edit = QTextEdit()
        json_edit.setPlaceholderText('粘贴 JSON 格式经历...\n例: [{"title": "...", "type": "work"}]')
        file_edit = QTextEdit()
        file_edit.setPlaceholderText("选择文件后，LLM 将自动分析文件内容并提取结构化经历...")
        file_edit.setReadOnly(True)
        tabs.addTab(md_edit, "Markdown")
        tabs.addTab(text_edit, "纯文本")
        tabs.addTab(json_edit, "JSON")
        tabs.addTab(file_edit, "文件")
        layout.addWidget(tabs)

        # 底部按钮
        btn_bar = QHBoxLayout()
        btn_bar.addStretch()

        btn_load_file = QPushButton("从文件加载")
        btn_load_file.clicked.connect(lambda: self._load_import_file(tabs, md_edit, text_edit, json_edit, file_edit))
        btn_bar.addWidget(btn_load_file)

        btn_import = QPushButton("导入")
        btn_import.setStyleSheet("QPushButton { background-color: #27ae60; color: white; padding: 6px 24px; }")
        btn_import.clicked.connect(lambda: self._do_import(dialog, tabs, md_edit, text_edit, json_edit, file_edit))
        btn_bar.addWidget(btn_import)

        btn_cancel = QPushButton("取消")
        btn_cancel.clicked.connect(dialog.reject)
        btn_bar.addWidget(btn_cancel)
        layout.addLayout(btn_bar)

        dialog.exec()

    def _load_import_file(self, tabs: Any, md_edit: Any, text_edit: Any, json_edit: Any, file_edit: Any) -> None:
        """从文件加载导入内容"""
        filepath, _filter = QFileDialog.getOpenFileName(
            self, "选择经历文件", "", "All Supported (*.md *.txt *.json *.pdf *.docx);;Markdown (*.md);;Text (*.txt);;JSON (*.json);;PDF (*.pdf);;Word (*.docx);;All Files (*.*)"
        )
        if not filepath:
            return
        try:
            path = Path(filepath)
            if filepath.endswith(".pdf") or filepath.endswith(".docx"):
                # PDF/Word 切换到文件 Tab，只显示文件名和提示
                tabs.setCurrentIndex(3)
                file_edit.setPlainText(f"已选择文件: {path.name}\n点击「导入」按钮，LLM 将自动分析文件内容并提取经历。")
                file_edit.setProperty("_file_path", filepath)
            else:
                content = path.read_text(encoding="utf-8")
                if filepath.endswith(".md"):
                    tabs.setCurrentIndex(0)
                    md_edit.setPlainText(content)
                elif filepath.endswith(".json"):
                    tabs.setCurrentIndex(2)
                    json_edit.setPlainText(content)
                else:
                    tabs.setCurrentIndex(1)
                    text_edit.setPlainText(content)
        except Exception as exc:
            QMessageBox.critical(self, "读取失败", f"无法读取文件:\n{exc}")

    def _do_import(self, dialog: Any, tabs: Any, md_edit: Any, text_edit: Any, json_edit: Any, file_edit: Any) -> None:
        """执行导入"""
        from src.services.import_parser import ImportParser, ImportParserError

        idx = tabs.currentIndex()
        if idx == 3:
            # 文件模式：调用 LLM 分析
            self._do_file_import(dialog, file_edit)
            return
        elif idx == 0:
            text = md_edit.toPlainText().strip()
            if not text:
                QMessageBox.warning(self, "空内容", "请先粘贴 Markdown 内容。")
                return
            parser_method = ImportParser().parse_markdown
        elif idx == 2:
            text = json_edit.toPlainText().strip()
            if not text:
                QMessageBox.warning(self, "空内容", "请先粘贴 JSON 内容。")
                return
            parser_method = ImportParser().parse_json
        else:
            text = text_edit.toPlainText().strip()
            if not text:
                QMessageBox.warning(self, "空内容", "请先粘贴文本内容。")
                return
            parser_method = ImportParser().parse_text

        try:
            async def import_and_reload() -> tuple[int, int, List[Experience]]:
                drafts = await parser_method(text)
                if not drafts:
                    return 0, 0, await self.manager.list_by_user(status_filter="confirmed")

                success = 0
                for draft in drafts:
                    try:
                        await self.manager.confirm_and_save(draft)
                        success += 1
                    except Exception as e:
                        logger.warning("导入单条经历失败: %s", e)

                exps = await self.manager.list_by_user(status_filter="confirmed")
                return success, len(drafts), exps

            def on_success(result: tuple[int, int, List[Experience]]) -> None:
                success, total, exps = result
                if total == 0:
                    QMessageBox.information(self, "无数据", "未能解析出有效的经历，请检查格式。")
                    return
                self._populate_experiences(exps)
                QMessageBox.information(
                    self, "导入完成",
                    f"成功导入 {success} / {total} 条经历。"
                )
                dialog.accept()

            start_async_task(
                self,
                self.status_label,
                "正在导入经历...",
                import_and_reload,
                on_success,
                self._show_task_error("导入失败"),
                [self.btn_import, self.btn_refresh, self.btn_save, self.btn_delete],
            )
        except ImportParserError as exc:
            QMessageBox.critical(self, "解析失败", f"格式解析失败:\n{exc}")
        except Exception as exc:
            QMessageBox.critical(self, "导入失败", f"导入过程中出错:\n{exc}")

    def _do_file_import(self, dialog: Any, file_edit: Any) -> None:
        """文件导入：调用 LLM 分析并留痕"""
        filepath = file_edit.property("_file_path")
        if not filepath:
            QMessageBox.warning(self, "未选择文件", "请先点击「从文件加载」选择要分析的文件。")
            return

        path = Path(filepath)
        if not path.exists():
            QMessageBox.critical(self, "文件不存在", f"文件不存在: {filepath}")
            return

        # 读取文件内容
        try:
            if path.suffix.lower() == ".pdf":
                try:
                    import pymupdf
                    doc = pymupdf.open(filepath)
                    content = "\n".join(page.get_text() for page in doc)
                except ImportError:
                    QMessageBox.warning(self, "缺少依赖", "PDF 解析需要 PyMuPDF。\n请运行: pip install pymupdf")
                    return
            elif path.suffix.lower() == ".docx":
                try:
                    import docx
                    d = docx.Document(filepath)
                    content = "\n".join(p.text for p in d.paragraphs if p.text.strip())
                except ImportError:
                    QMessageBox.warning(self, "缺少依赖", "Word 解析需要 python-docx。\n请运行: pip install python-docx")
                    return
            else:
                content = path.read_text(encoding="utf-8")
        except Exception as exc:
            QMessageBox.critical(self, "读取失败", f"无法读取文件:\n{exc}")
            return

        file_type_map = {
            ".md": "Markdown",
            ".txt": "纯文本",
            ".json": "JSON",
            ".pdf": "PDF",
            ".docx": "Word",
        }
        file_type = file_type_map.get(path.suffix.lower(), "未知")

        async def analyze_and_import() -> tuple[int, int, List[Experience]]:
            parser = ImportParser()
            drafts = await parser.analyze_file_with_llm(content, file_type=f"{file_type}文件")

            success = 0
            for draft in drafts:
                try:
                    await self.manager.confirm_and_save(draft)
                    success += 1
                except Exception as e:
                    logger.warning("LLM 导入单条经历失败: %s", e)

            exps = await self.manager.list_by_user(status_filter="confirmed")

            # 保存上传记录
            from src.models.database import AsyncSessionLocal
            from src.models.entities import UploadedFile
            async with AsyncSessionLocal() as session:
                record = UploadedFile(
                    filename=path.name,
                    file_type=file_type,
                    content_preview=content[:500] if content else None,
                    extracted_count=success,
                    status="processed" if success > 0 else "failed",
                )
                session.add(record)
                await session.commit()

            return success, len(drafts), exps

        def on_success(result: tuple[int, int, List[Experience]]) -> None:
            success, total, exps = result
            self._populate_experiences(exps)
            if success > 0:
                QMessageBox.information(
                    self, "导入完成",
                    f"LLM 分析完成！\n成功导入 {success} / {total} 条经历。\n\n上传记录已保存。"
                )
                dialog.accept()
            else:
                QMessageBox.warning(
                    self, "未能导入",
                    f"LLM 分析未能提取有效经历。\n共分析出 {total} 条，但都未能成功导入。\n请检查文件内容或手动粘贴。"
                )

        start_async_task(
            self,
            self.status_label,
            f"LLM 正在分析 {path.name}...",
            analyze_and_import,
            on_success,
            self._show_task_error("文件分析失败"),
            [self.btn_import, self.btn_refresh, self.btn_save, self.btn_delete],
        )
