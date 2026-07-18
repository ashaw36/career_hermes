"""
CareerCraft Agent — 岗位匹配页面

核心职责：JD 列表、粘贴解析、匹配计算、结果展示。
Sprint 6 GUI 扩展。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.services.jd_reframe_engine import JDReframeEngine
from src.services.job_matcher import JobMatcher
from src.services.job_parser import JobParser
from src.services.persona_engine import PersonaEngine
from src.ui.async_tasks import start_async_task

logger = logging.getLogger(__name__)


class JobMatchPage(QWidget):
    """
    岗位匹配页面

    布局：
    - 顶部：角色选择 + 粘贴 JD + 解析匹配按钮
    - 左侧：JD 列表（含删除操作）
    - 右侧：匹配结果详情 + 简历修饰功能
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._persona_engine = PersonaEngine()
        self._job_parser = JobParser()
        self._job_matcher = JobMatcher()
        self._jd_reframe_engine = JDReframeEngine()
        self._personas: List[Any] = []
        self._current_job_id: Optional[str] = None
        self._current_match_id: Optional[str] = None
        self._async_tasks: set[Any] = set()
        self._init_ui()
        self._load_personas()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 顶部控制栏
        top_bar = QHBoxLayout()

        self._persona_combo = QComboBox()
        self._persona_combo.setMinimumWidth(200)
        top_bar.addWidget(QLabel("角色:"))
        top_bar.addWidget(self._persona_combo)

        self._jd_input = QPlainTextEdit()
        self._jd_input.setPlaceholderText("在此粘贴岗位描述 (JD)...")
        self._jd_input.setMaximumHeight(80)
        top_bar.addWidget(self._jd_input, stretch=1)

        self._parse_btn = QPushButton("解析并匹配")
        self._parse_btn.setStyleSheet(
            "QPushButton { background-color: #2196F3; color: white; padding: 8px 16px; }"
        )
        self._parse_btn.clicked.connect(self._on_parse_and_match)
        top_bar.addWidget(self._parse_btn)

        layout.addLayout(top_bar)

        self._status_label = QLabel()
        self._status_label.setStyleSheet("color: #666;")
        layout.addWidget(self._status_label)

        # 分隔线
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # 左侧：JD 列表
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(QLabel("已解析的岗位"))

        self._job_table = QTableWidget()
        self._job_table.setColumnCount(5)
        self._job_table.setHorizontalHeaderLabels(["岗位名称", "公司", "地点", "查看", "删除"])
        self._job_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._job_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._job_table.horizontalHeader().setStretchLastSection(True)
        self._job_table.cellClicked.connect(self._on_job_selected)
        left_layout.addWidget(self._job_table)

        # 行号到 job_id 映射
        self._job_id_map: List[str] = []

        self._refresh_btn = QPushButton("刷新列表")
        self._refresh_btn.clicked.connect(self._load_job_list)
        left_layout.addWidget(self._refresh_btn)

        splitter.addWidget(left_panel)

        # 右侧：匹配详情
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)

        self._match_score_label = QLabel("请选择岗位查看匹配度")
        self._match_score_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        right_layout.addWidget(self._match_score_label)

        self._match_detail = QTextEdit()
        self._match_detail.setReadOnly(True)
        right_layout.addWidget(self._match_detail)

        # 简历修饰区
        reframe_bar = QHBoxLayout()
        self._reframe_btn = QPushButton("✏️ 修饰简历以匹配此岗位")
        self._reframe_btn.setStyleSheet(
            "QPushButton { background-color: #9b59b6; color: white; padding: 6px 16px; }"
        )
        self._reframe_btn.setEnabled(False)
        self._reframe_btn.clicked.connect(self._on_reframe_resume)
        reframe_bar.addWidget(self._reframe_btn)
        reframe_bar.addStretch()
        right_layout.addLayout(reframe_bar)

        self._reframe_detail = QTextEdit()
        self._reframe_detail.setReadOnly(True)
        self._reframe_detail.setPlaceholderText("点击「修饰简历」后，将展示针对此岗位优化后的经历描述...")
        self._reframe_detail.setMaximumHeight(200)
        right_layout.addWidget(self._reframe_detail)

        # 状态更新
        status_bar = QHBoxLayout()
        self._status_combo = QComboBox()
        self._status_combo.addItems([
            "new", "interested", "applied", "interviewing",
            "offered", "rejected", "ghosted", "accepted", "declined",
        ])
        status_bar.addWidget(QLabel("更新状态:"))
        status_bar.addWidget(self._status_combo)

        self._update_status_btn = QPushButton("保存状态")
        self._update_status_btn.clicked.connect(self._on_update_status)
        status_bar.addWidget(self._update_status_btn)
        status_bar.addStretch()

        right_layout.addLayout(status_bar)
        splitter.addWidget(right_panel)
        splitter.setSizes([400, 600])

        layout.addWidget(splitter, stretch=1)

    def _load_personas(self) -> None:
        """加载角色列表"""
        def on_success(personas: List[Any]) -> None:
            self._personas = personas
            self._persona_combo.clear()
            for p in personas:
                self._persona_combo.addItem(p.name, p.id)

        start_async_task(
            self,
            self._status_label,
            "正在加载角色...",
            self._persona_engine.list_by_user,
            on_success,
            self._show_task_error("加载角色失败"),
            [self._persona_combo, self._parse_btn, self._refresh_btn],
        )

    def _load_job_list(self) -> None:
        """加载 JD 列表"""
        start_async_task(
            self,
            self._status_label,
            "正在加载岗位列表...",
            lambda: self._job_parser.list_all(limit=50),
            self._populate_job_list,
            self._show_task_error("加载岗位列表失败"),
            [self._refresh_btn, self._parse_btn],
        )

    def _populate_job_list(self, jobs: List[Any]) -> None:
        self._job_id_map = []
        self._job_table.setRowCount(len(jobs))
        for i, job in enumerate(jobs):
            self._job_id_map.append(job.id)
            self._job_table.setItem(i, 0, QTableWidgetItem(job.title or "未命名"))
            self._job_table.setItem(i, 1, QTableWidgetItem(job.company or "-"))
            self._job_table.setItem(i, 2, QTableWidgetItem(job.location or "-"))

            view_btn = QPushButton("查看")
            view_btn.clicked.connect(lambda checked, jid=job.id: self._on_view_job(jid))
            self._job_table.setCellWidget(i, 3, view_btn)

            del_btn = QPushButton("删除")
            del_btn.setStyleSheet("QPushButton { color: #e74c3c; }")
            del_btn.clicked.connect(lambda checked, jid=job.id: self._on_delete_job(jid))
            self._job_table.setCellWidget(i, 4, del_btn)

        self._job_table.resizeColumnsToContents()

    def _show_task_error(self, title: str) -> Any:
        def _handler(exc: Exception) -> None:
            logger.error("%s: %s", title, exc)
            QMessageBox.critical(self, "错误", f"{title}: {exc}")

        return _handler

    def _on_parse_and_match(self) -> None:
        """粘贴 JD → 解析 → 匹配"""
        raw_text = self._jd_input.toPlainText().strip()
        if not raw_text:
            QMessageBox.warning(self, "警告", "请先粘贴岗位描述")
            return

        persona_id = self._persona_combo.currentData()
        if not persona_id:
            QMessageBox.warning(self, "警告", "请先选择一个角色")
            return

        async def parse_match_and_reload() -> tuple[str, Any, List[Any]]:
            # 1. 解析 JD
            job_desc = await self._job_parser.parse_and_save(raw_text, source="manual")
            # 2. 匹配
            match = await self._job_matcher.match(persona_id, job_desc.id)
            jobs = await self._job_parser.list_all(limit=50)
            return job_desc.id, match, jobs

        def on_success(result: tuple[str, Any, List[Any]]) -> None:
            job_id, match, jobs = result
            self._current_job_id = job_id
            self._display_match(match)
            self._populate_job_list(jobs)
            self._jd_input.clear()

        start_async_task(
            self,
            self._status_label,
            "正在解析并匹配...",
            parse_match_and_reload,
            on_success,
            self._show_task_error("解析匹配失败"),
            [self._parse_btn, self._refresh_btn, self._update_status_btn, self._persona_combo],
        )

    def _on_job_selected(self, row: int, column: int) -> None:
        """点击列表中的岗位"""
        if 0 <= row < len(self._job_id_map):
            job_id = self._job_id_map[row]
            self._on_view_job(job_id)

    def _on_view_job(self, job_id: str) -> None:
        """查看某个岗位的匹配结果"""
        persona_id = self._persona_combo.currentData()
        if not persona_id:
            QMessageBox.warning(self, "警告", "请先选择角色")
            return

        async def load_match() -> Any:
            # 检查是否已有匹配记录
            matches = await self._job_matcher.list_matches(persona_id)
            target_match = None
            for m in matches:
                if m.job_desc_id == job_id:
                    target_match = m
                    break

            if not target_match:
                # 重新计算匹配
                target_match = await self._job_matcher.match(persona_id, job_id)
            return target_match

        def on_success(target_match: Any) -> None:
            self._current_job_id = job_id
            self._display_match(target_match)

        start_async_task(
            self,
            self._status_label,
            "正在加载匹配结果...",
            load_match,
            on_success,
            self._show_task_error("查看匹配失败"),
            [self._parse_btn, self._refresh_btn, self._update_status_btn],
        )

    def _display_match(self, match: Any) -> None:
        """显示匹配结果"""
        score = match.match_score
        color = "#4CAF50" if score >= 80 else "#FF9800" if score >= 50 else "#F44336"
        self._match_score_label.setText(
            f"综合匹配度: <span style='color: {color};'>{score}/100</span>"
        )

        lines = [
            f"### 匹配分项",
            f"- 技能匹配: {match.score_breakdown.get('skill', 0)} / 50",
            f"- 经验匹配: {match.score_breakdown.get('experience', 0)} / 25",
            f"- 文本相似度: {match.score_breakdown.get('text_similarity', 0)} / 15",
            f"- 其他匹配: {match.score_breakdown.get('other', 0)} / 10",
            f"",
            f"### 匹配技能 ({len(match.matched_skills or [])} 个)",
        ]
        for skill in match.matched_skills or []:
            lines.append(f"✅ {skill}")

        lines.extend([f"", f"### 缺失技能 ({len(match.missing_skills or [])} 个)"])
        for skill in match.missing_skills or []:
            lines.append(f"❌ {skill}")

        lines.extend([f"", f"### 投递状态", f"{match.tracking_status}"])

        self._match_detail.setText("\n".join(lines))
        self._status_combo.setCurrentText(match.tracking_status)

        # 保存当前 match_id 并启用修饰按钮
        self._current_match_id = match.id
        self._reframe_btn.setEnabled(True)
        self._reframe_detail.clear()
        self._reframe_detail.setPlaceholderText("点击「修饰简历」后，将展示针对此岗位优化后的经历描述...")

        # 检查是否已有缓存的修饰结果
        start_async_task(
            self,
            self._status_label,
            "检查缓存修饰结果...",
            lambda: self._jd_reframe_engine.get_reframed_experiences(match.id),
            self._display_reframed_experiences,
            lambda exc: logger.debug("无缓存修饰结果: %s", exc),
            [],
        )

    def _on_update_status(self) -> None:
        """更新投递状态"""
        if not self._current_job_id:
            QMessageBox.warning(self, "警告", "请先选择或解析一个岗位")
            return

        persona_id = self._persona_combo.currentData()
        if not persona_id:
            return

        new_status = self._status_combo.currentText()

        async def update_status() -> bool:
            # 找到对应的 match_id
            matches = await self._job_matcher.list_matches(persona_id)
            target_match = None
            for m in matches:
                if m.job_desc_id == self._current_job_id:
                    target_match = m
                    break

            if target_match:
                await self._job_matcher.update_tracking_status(target_match.id, new_status)
                return True
            return False

        def on_success(updated: bool) -> None:
            if updated:
                QMessageBox.information(self, "成功", f"状态已更新为: {new_status}")
            else:
                QMessageBox.warning(self, "警告", "未找到匹配记录")

        start_async_task(
            self,
            self._status_label,
            "正在保存状态...",
            update_status,
            on_success,
            self._show_task_error("更新状态失败"),
            [self._update_status_btn, self._parse_btn, self._refresh_btn],
        )

    def _on_delete_job(self, job_id: str) -> None:
        """删除岗位"""
        reply = QMessageBox.question(
            self,
            "确认删除",
            "确定删除此岗位吗？相关的匹配记录也将被删除。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        async def do_delete() -> bool:
            # 先删除相关的修饰记录和匹配记录
            persona_id = self._persona_combo.currentData()
            if persona_id:
                matches = await self._job_matcher.list_matches(persona_id)
                for m in matches:
                    if m.job_desc_id == job_id:
                        await self._jd_reframe_engine.delete_reframes(m.id)
                        await self._job_matcher.delete_match(m.id)
            return await self._job_parser.delete(job_id)

        def on_success(deleted: bool) -> None:
            if deleted:
                QMessageBox.information(self, "成功", "岗位已删除")
                self._load_job_list()
                # 清空右侧显示
                self._match_score_label.setText("请选择岗位查看匹配度")
                self._match_detail.clear()
                self._reframe_detail.clear()
                self._reframe_btn.setEnabled(False)
                self._current_job_id = None
                self._current_match_id = None
            else:
                QMessageBox.warning(self, "失败", "删除岗位失败")

        start_async_task(
            self,
            self._status_label,
            "正在删除岗位...",
            do_delete,
            on_success,
            self._show_task_error("删除失败"),
            [self._refresh_btn, self._parse_btn],
        )

    def _on_reframe_resume(self) -> None:
        """修饰简历以匹配当前岗位"""
        if not self._current_match_id:
            QMessageBox.warning(self, "警告", "请先选择岗位并查看匹配结果")
            return

        reply = QMessageBox.question(
            self,
            "确认修饰",
            "是否重新修饰简历？\n\n将使用 LLM 根据岗位 JD 优化经历描述，可能需要一些时间。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        force = False
        # 如果已有缓存，询问是否强制刷新
        if self._reframe_detail.toPlainText().strip():
            reply2 = QMessageBox.question(
                self,
                "已有缓存",
                "已有缓存的修饰结果，是否强制重新修饰？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            force = reply2 == QMessageBox.StandardButton.Yes

        async def do_reframe() -> List[Any]:
            return await self._jd_reframe_engine.reframe_experiences_for_job(
                self._current_match_id, force_refresh=force
            )

        start_async_task(
            self,
            self._status_label,
            "正在修饰简历（可能需要几十秒）...",
            do_reframe,
            self._display_reframed_experiences,
            self._show_task_error("修饰失败"),
            [self._reframe_btn, self._update_status_btn, self._parse_btn],
        )

    def _display_reframed_experiences(self, reframes: List[Any]) -> None:
        """展示修饰后的经历"""
        if not reframes:
            self._reframe_detail.setPlainText("暂无修饰结果。\n\n点击「修饰简历」按钮以生成针对此岗位优化的经历描述。")
            return

        lines: List[str] = ["## 修饰后的经历\n"]
        for i, r in enumerate(reframes, 1):
            lines.append(f"### {i}. {r.original_summary[:40]}...")
            strategy = r.reframing_strategy or "未说明"
            lines.append("> **修饰策略**: " + strategy)
            lines.append("")
            lines.append(r.reframed_summary)
            lines.append("---\n")

        self._reframe_detail.setPlainText("\n".join(lines))
