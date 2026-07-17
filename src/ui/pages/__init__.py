"""
CareerCraft Agent — GUI 业务页面包

包含经历管理、角色配置、简历预览等核心页面。
"""

from __future__ import annotations

from src.ui.pages.experience_page import ExperiencePage
from src.ui.pages.job_match_page import JobMatchPage
from src.ui.pages.persona_page import PersonaPage
from src.ui.pages.resume_page import ResumePage

__all__ = [
    "ExperiencePage",
    "JobMatchPage",
    "PersonaPage",
    "ResumePage",
]
