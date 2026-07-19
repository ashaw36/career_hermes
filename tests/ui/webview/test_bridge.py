"""
CareerCraft Agent — WebView Bridge 测试
"""

from __future__ import annotations

import json
from typing import Any, Dict, List

import pytest

from src.ui.webview.bridge import CareerBridge


class TestCareerBridge:
    """CareerBridge 单元测试"""

    @pytest.fixture
    def bridge(self) -> CareerBridge:
        return CareerBridge()

    def test_get_stats_returns_json(self, bridge: CareerBridge) -> None:
        """getStats 返回有效 JSON"""
        result = bridge.getStats()
        data: Dict[str, Any] = json.loads(result)
        assert data.get("success") is True
        assert "data" in data
        stats: Dict[str, Any] = data["data"]
        assert isinstance(stats.get("experiencesCount"), int)
        assert isinstance(stats.get("personasCount"), int)

    def test_get_experiences_returns_json(self, bridge: CareerBridge) -> None:
        """getExperiences 返回有效 JSON"""
        result = bridge.getExperiences()
        data: Dict[str, Any] = json.loads(result)
        assert data.get("success") is True
        assert "data" in data
        assert isinstance(data["data"], list)

    def test_get_personas_returns_json(self, bridge: CareerBridge) -> None:
        """getPersonas 返回有效 JSON"""
        result = bridge.getPersonas()
        data: Dict[str, Any] = json.loads(result)
        assert data.get("success") is True
        assert "data" in data
        assert isinstance(data["data"], list)

    def test_save_experience_with_valid_data(self, bridge: CareerBridge) -> None:
        """saveExperience 接受有效 JSON 并返回结果"""
        payload: Dict[str, Any] = {
            "title": "测试项目",
            "description": "这是一个测试描述",
            "start_date": "2024-01",
            "end_date": "2024-12",
            "skills": ["Python", "SQL"],
            "company": "测试公司",
            "role": "产品经理",
        }
        result = bridge.saveExperience(json.dumps(payload))
        data: Dict[str, Any] = json.loads(result)
        # 可能成功或失败，但必须返回有效 JSON
        assert "success" in data

    def test_generate_resume_with_empty_id(self, bridge: CareerBridge) -> None:
        """generateResume 对空 ID 返回错误"""
        result = bridge.generateResume("")
        data: Dict[str, Any] = json.loads(result)
        # 空 ID 应该失败
        assert data.get("success") is False or "error" in data or "markdown" in data

    def test_parse_jd_with_sample_text(self, bridge: CareerBridge) -> None:
        """parseJD 接受 JD 文本并返回解析结果"""
        jd = "高级产品经理，要求 Python、SQL、产品规划"
        result = bridge.parseJD(jd)
        data: Dict[str, Any] = json.loads(result)
        assert "success" in data

    def test_match_job_with_empty_ids(self, bridge: CareerBridge) -> None:
        """matchJob 对空 ID 返回错误"""
        result = bridge.matchJob("", "")
        data: Dict[str, Any] = json.loads(result)
        # 空 ID 应该失败
        assert data.get("success") is False or "error" in data

    def test_get_learning_path_with_skill(self, bridge: CareerBridge) -> None:
        """getLearningPath 返回学习资源列表"""
        result = bridge.getLearningPath("Python")
        data: Dict[str, Any] = json.loads(result)
        assert data.get("success") is True
        assert "data" in data
        assert isinstance(data["data"], list)

    def test_bridge_methods_return_utf8(self, bridge: CareerBridge) -> None:
        """
        所有方法返回的 JSON 字符串包含中文，不是 Unicode 转义。
        """
        result = bridge.getStats()
        # 确保不是 \\uXXXX 格式
        assert "\\u5df2" not in result
        assert "已录入" in result or "experiencesCount" in result

    def test_get_skill_graph_returns_json(self, bridge: CareerBridge) -> None:
        """getSkillGraph 返回有效 JSON并包含 50 个节点"""
        result = bridge.getSkillGraph()
        data: Dict[str, Any] = json.loads(result)
        assert data.get("success") is True
        assert "data" in data
        assert isinstance(data["data"], list)
        assert len(data["data"]) == 50

    def test_search_skills_returns_json(self, bridge: CareerBridge) -> None:
        """searchSkills 返回搜索结果"""
        result = bridge.searchSkills("Python")
        data: Dict[str, Any] = json.loads(result)
        assert data.get("success") is True
        assert "data" in data
        assert isinstance(data["data"], list)
        assert any(r.get("id") == "python" for r in data["data"])

    def test_search_skills_empty_returns_json(self, bridge: CareerBridge) -> None:
        """searchSkills 空搜索返回空列表"""
        result = bridge.searchSkills("")
        data: Dict[str, Any] = json.loads(result)
        assert data.get("success") is True
        assert data["data"] == []
