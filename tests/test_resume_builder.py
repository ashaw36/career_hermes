"""Tests for Resume Builder"""
from __future__ import annotations

import pytest
from datetime import date
from unittest.mock import AsyncMock, patch, MagicMock

from src.services.resume_builder import ResumeBuilder


class TestResumeBuilder:
    """简历生成引擎测试"""

    @pytest.fixture
    def mock_persona(self):
        p = MagicMock()
        p.name = "AI产品经理"
        p.identity_statement = "专注于AI产品的策略与落地"
        p.career_narrative = ""
        p.tone_style = "business_insight"
        p.max_experiences = 5
        return p

    @pytest.fixture
    def mock_weighted_exp(self):
        """模拟带权重的经历"""
        rew = MagicMock()
        rew.relevance_score = 0.85
        rew.experience = MagicMock()
        rew.experience.title = "产品经理"
        rew.experience.organization = "美团"
        rew.experience.type = "work"
        rew.experience.start_date = date(2022, 1, 1)
        rew.experience.end_date = date(2023, 6, 1)
        rew.experience.structured_achievements = ["DAU提升30%"]
        rew.experience.skills_demonstrated = ["SQL", "Python"]
        rew.experience.metrics = ["30%"]
        rew.experience.raw_description = "负责增长"
        return rew

    @pytest.mark.asyncio
    async def test_build_context(self, mock_persona, mock_weighted_exp):
        """构建渲染上下文"""
        builder = ResumeBuilder(persona_id="test-id")
        builder._persona = mock_persona
        builder._experiences = [mock_weighted_exp]

        ctx = await builder._build_context()
        assert ctx["name"] == "AI产品经理"
        assert ctx["identity_statement"] == "专注于AI产品的策略与落地"
        assert len(ctx["experiences"]) == 1
        assert ctx["experiences"][0]["title"] == "产品经理"
        assert ctx["experiences"][0]["relevance_score"] == 0.85

    def test_format_period_both_dates(self):
        """格式化起止时间"""
        result = ResumeBuilder._format_period(
            date(2022, 1, 1), date(2023, 6, 1)
        )
        assert result == "2022.01 — 2023.06"

    def test_format_period_ongoing(self):
        """至今"""
        result = ResumeBuilder._format_period(date(2022, 1, 1), None)
        assert "2022.01" in result
        assert "至今" in result

    def test_format_period_none(self):
        """无日期"""
        result = ResumeBuilder._format_period(None, None)
        assert result == "? — 至今"
