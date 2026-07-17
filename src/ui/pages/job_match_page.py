"""
CareerCraft Agent — 岗位匹配页面

核心职责：JD 列表、粘贴解析、匹配计算、结果展示。
Sprint 6 GUI 扩展。
"""

from __future__ import annotations

import asyncio
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

from src.services.job_matcher import JobMatcher
from src.services.job_parser import JobParser
from src.services.persona_engine import PersonaEngine

logger = logging.getLogger(__name__)


class JobMatchPage(QWidget):
    """
    岗位匹配页面

    布局：
    - 顶部：角色选择 + 粘贴 JD + 解析匹配按钮
    - 左侧：JD 列表
    - 右侧：匹配结果详情
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._persona_engine = PersonaEngine()
        self._job_parser = JobParser()
        self._job_matcher = JobMatcher()
        self._personas: List[Any] = []
        self._current_job_id: Optional[str] = None
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

        # 分隔线
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # 左侧：JD 列表
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(QLabel("已解析的岗位"))

        self._job_table = QTableWidget()
        self._job_table.setColumnCount(4)
        self._job_table.setHorizontalHeaderLabels(["岗位名称", "公司", "地点", "操作"])
        self._job_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._job_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._job_table.horizontalHeader().setStretchLastSection(True)
        self._job_table.cellClicked.connect(self._on_job_selected)
        left_layout.addWidget(self._job_table)

        refresh_btn = QPushButton("刷新列表")
        refresh_btn.clicked.connect(self._load_job_list)
        left_layout.addWidget(refresh_btn)

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

    def _run_async(self, coro: Any) -> Any:
        """静态辅助：运行异步协程"""
        try:
            return asyncio.run(coro)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(coro)

    def _load_personas(self) -> None:
        """加载角色列表"""
        try:
            personas = self._run_async(self._persona_engine.list_by_user())
            self._personas = personas
            self._persona_combo.clear()
            for p in personas:
                self._persona_combo.addItem(p.name, p.id)
        except Exception as e:
            logger.error("加载角色失败: %s", e)

    def _load_job_list(self) -> None:
        """加载 JD 列表"""
        try:
            jobs = self._run_async(self._job_parser.list_all(limit=50))
            self._job_table.setRowCount(len(jobs))
            for i, job in enumerate(jobs):
                self._job_table.setItem(i, 0, QTableWidgetItem(job.title or "未命名"))
                self._job_table.setItem(i, 1, QTableWidgetItem(job.company or "-"))
                self._job_table.setItem(i, 2, QTableWidgetItem(job.location or "-"))
                btn = QPushButton("查看")
                btn.clicked.connect(lambda checked, jid=job.id: self._on_view_job(jid))
                self._job_table.setCellWidget(i, 3, btn)
            self._job_table.resizeColumnsToContents()
        except Exception as e:
            logger.error("加载岗位列表失败: %s", e)

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

        self._parse_btn.setEnabled(False)
        self._parse_btn.setText("解析中...")

        try:
            # 1. 解析 JD
            job_desc = self._run_async(
                self._job_parser.parse_and_save(raw_text, source="manual")
            )
            # 2. 匹配
            match = self._run_async(
                self._job_matcher.match(persona_id, job_desc.id)
            )
            # 3. 显示结果
            self._current_job_id = job_desc.id
            self._display_match(match)
            self._load_job_list()
            self._jd_input.clear()
        except Exception as e:
            logger.error("解析匹配失败: %s", e)
            QMessageBox.critical(self, "错误", f"解析匹配失败: {e}")
        finally:
            self._parse_btn.setEnabled(True)
            self._parse_btn.setText("解析并匹配")

    def _on_job_selected(self, row: int, column: int) -> None:
        """点击列表中的岗位"""
        # 通过行号获取 job_id 比较困难，这里简化处理
        pass

    def _on_view_job(self, job_id: str) -> None:
        """查看某个岗位的匹配结果"""
        persona_id = self._persona_combo.currentData()
        if not persona_id:
            QMessageBox.warning(self, "警告", "请先选择角色")
            return

        try:
            # 检查是否已有匹配记录
            matches = self._run_async(
                self._job_matcher.list_matches(persona_id)
            )
            target_match = None
            for m in matches:
                if m.job_desc_id == job_id:
                    target_match = m
                    break

            if not target_match:
                # 重新计算匹配
                target_match = self._run_async(
                    self._job_matcher.match(persona_id, job_id)
                )

            self._current_job_id = job_id
            self._display_match(target_match)
        except Exception as e:
            logger.error("查看匹配失败: %s", e)
            QMessageBox.critical(self, "错误", f"查看匹配失败: {e}")

    def _display_match(self, match: Any) -> None:
        """显示匹配结果"""
        score = match.match_score
        color = "#4CAF50" if score >= 80 else "#FF9800" if score >= 50 else "#F44336"
        self._match_score_label.setText(
            f"综合匹配度: <span style='color: {color};'>{score}/100</span>"
        )

        lines = [
            f"### 匹配分项",
            f"- 技能匹配: {match.score_breakdown.get('skill', 0)} / 60",
            f"- 经验匹配: {match.score_breakdown.get('experience', 0)} / 30",
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

    def _on_update_status(self) -> None:
        """更新投递状态"""
        if not self._current_job_id:
            QMessageBox.warning(self, "警告", "请先选择或解析一个岗位")
            return

        persona_id = self._persona_combo.currentData()
        if not persona_id:
            return

        new_status = self._status_combo.currentText()

        try:
            # 找到对应的 match_id
            matches = self._run_async(
                self._job_matcher.list_matches(persona_id)
            )
            target_match = None
            for m in matches:
                if m.job_desc_id == self._current_job_id:
                    target_match = m
                    break

            if target_match:
                self._run_async(
                    self._job_matcher.update_tracking_status(target_match.id, new_status)
                )
                QMessageBox.information(self, "成功", f"状态已更新为: {new_status}")
            else:
                QMessageBox.warning(self, "警告", "未找到匹配记录")
        except Exception as e:
            logger.error("更新状态失败: %s", e)
            QMessageBox.critical(self, "错误", f"更新状态失败: {e}")
