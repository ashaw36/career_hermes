"""
CareerCraft Agent — 角色配置页面

左侧角色列表，右侧详情编辑。支持动态增删 capability_weights。
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional, Tuple

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.models.entities import Persona
from src.services.persona_engine import PersonaEngine


class CapabilityWeightItem(QWidget):
    """单个能力权重编辑行。"""

    def __init__(self, skill: str = "", weight: int = 50, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.edit_skill = QLineEdit(skill)
        self.edit_skill.setPlaceholderText("技能名称")
        self.edit_skill.setMinimumWidth(120)
        layout.addWidget(self.edit_skill)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 100)
        self.slider.setValue(weight)
        self.slider.setMinimumWidth(120)
        layout.addWidget(self.slider)

        self.lbl_value = QLabel(f"{weight}")
        self.lbl_value.setFixedWidth(30)
        layout.addWidget(self.lbl_value)

        self.btn_remove = QPushButton("删除")
        self.btn_remove.setFixedWidth(50)
        layout.addWidget(self.btn_remove)

        self.slider.valueChanged.connect(lambda v: self.lbl_value.setText(str(v)))

    def get_data(self) -> Tuple[str, int]:
        """获取当前数据。"""
        return self.edit_skill.text().strip(), self.slider.value()


class PersonaPage(QWidget):
    """角色配置页面"""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.engine = PersonaEngine()
        self._current_persona_id: Optional[str] = None
        self._personas: List[Persona] = []
        self._weight_items: List[CapabilityWeightItem] = []

        self._init_ui()
        self._load_data()

    def _init_ui(self) -> None:
        """初始化界面"""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)

        # 左侧列表
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        toolbar = QHBoxLayout()
        self.btn_new = QPushButton("新建角色")
        self.btn_new.setToolTip("创建新角色档案")
        self.btn_delete = QPushButton("删除")
        self.btn_delete.setToolTip("删除选中角色")
        self.btn_refresh = QPushButton("刷新")
        self.btn_refresh.setToolTip("重新加载角色列表")
        toolbar.addWidget(self.btn_new)
        toolbar.addWidget(self.btn_delete)
        toolbar.addStretch()
        toolbar.addWidget(self.btn_refresh)
        left_layout.addLayout(toolbar)

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.list_widget.setSpacing(4)
        left_layout.addWidget(self.list_widget)

        splitter.addWidget(left_panel)

        # 右侧表单
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        form_container = QWidget()
        form_layout = QFormLayout(form_container)
        form_layout.setContentsMargins(16, 16, 16, 16)
        form_layout.setSpacing(12)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.edit_name = QLineEdit()
        self.edit_name.setPlaceholderText("例：产品经理角色")
        form_layout.addRow("名称：", self.edit_name)

        self.edit_identity = QTextEdit()
        self.edit_identity.setPlaceholderText("身份声明，简洁描述核心竞争力...")
        self.edit_identity.setMaximumHeight(80)
        form_layout.addRow("身份声明：", self.edit_identity)

        self.edit_narrative = QTextEdit()
        self.edit_narrative.setPlaceholderText("职业叙事，展现职业发展轨迹...")
        self.edit_narrative.setMaximumHeight(80)
        form_layout.addRow("职业叙事：", self.edit_narrative)

        self.combo_tone = QComboBox()
        self.combo_tone.addItems(["data_driven", "business_insight", "technical_deep"])
        form_layout.addRow("语气风格：", self.combo_tone)

        self.edit_targets = QLineEdit()
        self.edit_targets.setPlaceholderText("目标岗位，多个用英文逗号分隔")
        form_layout.addRow("目标岗位：", self.edit_targets)

        self.spin_max_exp = QSpinBox()
        self.spin_max_exp.setRange(1, 20)
        self.spin_max_exp.setValue(5)
        form_layout.addRow("最大经历数：", self.spin_max_exp)

        # 能力权重区域
        weights_header = QHBoxLayout()
        weights_header.addWidget(QLabel("能力权重："))
        weights_header.addStretch()
        self.btn_add_weight = QPushButton("添加权重")
        weights_header.addWidget(self.btn_add_weight)
        form_layout.addRow(weights_header)

        self.weights_container = QWidget()
        self.weights_layout = QVBoxLayout(self.weights_container)
        self.weights_layout.setContentsMargins(0, 0, 0, 0)
        self.weights_layout.setSpacing(6)
        self.weights_layout.addStretch()
        form_layout.addRow(self.weights_container)

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
        self.btn_refresh.clicked.connect(self._load_data)
        self.btn_save.clicked.connect(self._on_save)
        self.btn_add_weight.clicked.connect(self._add_weight_item)
        self.list_widget.currentItemChanged.connect(self._on_item_changed)

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

    def _load_data(self) -> None:
        """加载角色列表。"""
        self.list_widget.clear()
        self._personas = self._run_async(self.engine.list_by_user())
        for p in self._personas:
            item = QListWidgetItem(p.name)
            item.setData(Qt.ItemDataRole.UserRole, p.id)
            self.list_widget.addItem(item)
        self._clear_form()

    def _on_item_changed(self, current: Optional[QListWidgetItem], _previous: Optional[QListWidgetItem]) -> None:
        """列表项切换时加载详情。"""
        if current is None:
            self._clear_form()
            return
        persona_id = current.data(Qt.ItemDataRole.UserRole)
        persona = self._run_async(self.engine.get_by_id(persona_id))
        if persona is None:
            return
        self._current_persona_id = persona.id
        self.edit_name.setText(persona.name)
        self.edit_identity.setPlainText(persona.identity_statement or "")
        self.edit_narrative.setPlainText(persona.career_narrative or "")
        self.combo_tone.setCurrentText(persona.tone_style or "business_insight")
        targets = ", ".join(persona.target_job_profiles or [])
        self.edit_targets.setText(targets)
        self.spin_max_exp.setValue(persona.max_experiences)

        # 加载能力权重
        self._clear_weights()
        weights = persona.capability_weights or {}
        for skill, weight in weights.items():
            self._add_weight_item(skill, int(weight * 100))

    def _clear_form(self) -> None:
        """清空表单。"""
        self._current_persona_id = None
        self.edit_name.clear()
        self.edit_identity.clear()
        self.edit_narrative.clear()
        self.combo_tone.setCurrentIndex(1)
        self.edit_targets.clear()
        self.spin_max_exp.setValue(5)
        self._clear_weights()

    def _clear_weights(self) -> None:
        """清空所有能力权重项。"""
        for item in self._weight_items:
            item.setParent(None)
        self._weight_items.clear()

    def _add_weight_item(self, skill: str = "", weight: int = 50) -> None:
        """添加一个能力权重项。"""
        item = CapabilityWeightItem(skill, weight)
        item.btn_remove.clicked.connect(lambda _checked, w=item: self._remove_weight_item(w))
        # 插入到 stretch 之前
        self.weights_layout.insertWidget(self.weights_layout.count() - 1, item)
        self._weight_items.append(item)

    def _remove_weight_item(self, item: CapabilityWeightItem) -> None:
        """移除指定的能力权重项。"""
        if item in self._weight_items:
            self._weight_items.remove(item)
            item.setParent(None)

    def _on_new(self) -> None:
        """新建角色：清空表单并聚焦。"""
        self.list_widget.clearSelection()
        self._clear_form()
        self.edit_name.setFocus()

    def _on_delete(self) -> None:
        """删除当前选中角色。"""
        item = self.list_widget.currentItem()
        if item is None:
            QMessageBox.information(self, "提示", "请先选择要删除的角色。")
            return
        persona_id = item.data(Qt.ItemDataRole.UserRole)
        reply = QMessageBox.question(
            self,
            "确认删除",
            "确定要删除该角色吗？此操作不可恢复。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        ok = self._run_async(self.engine.delete(persona_id))
        if ok:
            self._load_data()
            QMessageBox.information(self, "成功", "角色已删除。")
        else:
            QMessageBox.warning(self, "失败", "删除角色失败。")

    def _on_save(self) -> None:
        """保存角色表单。"""
        name = self.edit_name.text().strip()
        if not name:
            QMessageBox.warning(self, "校验失败", "名称为必填项。")
            return

        identity = self.edit_identity.toPlainText().strip() or None
        narrative = self.edit_narrative.toPlainText().strip() or None
        tone = self.combo_tone.currentText()
        targets = [t.strip() for t in self.edit_targets.text().split(",") if t.strip()]
        max_exp = self.spin_max_exp.value()

        # 收集权重
        weights: Dict[str, float] = {}
        for item in self._weight_items:
            skill, weight = item.get_data()
            if skill:
                weights[skill] = weight / 100.0

        data: Dict[str, Any] = {
            "name": name,
            "identity_statement": identity,
            "career_narrative": narrative,
            "tone_style": tone,
            "capability_weights": weights or None,
            "target_job_profiles": targets or None,
            "max_experiences": max_exp,
        }

        if self._current_persona_id:
            persona = self._run_async(self.engine.update(self._current_persona_id, **data))
            if persona:
                QMessageBox.information(self, "成功", "角色已更新。")
            else:
                QMessageBox.warning(self, "失败", "更新角色失败。")
        else:
            persona = self._run_async(self.engine.create(**data))
            self._current_persona_id = persona.id
            QMessageBox.information(self, "成功", "角色已创建。")

        self._load_data()
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item and item.data(Qt.ItemDataRole.UserRole) == self._current_persona_id:
                self.list_widget.setCurrentItem(item)
                break
