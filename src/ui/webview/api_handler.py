"""
CareerCraft Agent — WebView API 同步适配层

将异步 Service 封装为同步 API，供 QWebChannel Bridge 调用。
在后台线程中运行 async 代码，避免与 Qt 主事件循环冲突。
"""

from __future__ import annotations

import asyncio
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional

from src.services.experience_manager import ExperienceManager
from src.services.job_matcher import JobMatcher
from src.services.learning_recommender import LearningRecommender
from src.services.persona_engine import PersonaEngine
from src.services.resume_builder import ResumeBuilder

logger = logging.getLogger(__name__)


class AsyncRunner:
    """在独立线程中运行 async 协程，返回同步结果"""

    _executor: Optional[ThreadPoolExecutor] = None

    @classmethod
    def _get_executor(cls) -> ThreadPoolExecutor:
        if cls._executor is None:
            cls._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="career_async")
        return cls._executor

    @classmethod
    def run(cls, coro: Any) -> Any:
        """提交协程到后台线程执行，阻塞等待结果"""
        def _run() -> Any:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(coro)
            finally:
                loop.close()

        future = cls._get_executor().submit(_run)
        return future.result(timeout=15)


class CareerAPI:
    """
    同步 API 封装，直接供 Bridge 调用
    服务实例延迟初始化，避免导入时阻塞。
    """

    def __init__(self) -> None:
        self._exp_mgr: Optional[ExperienceManager] = None
        self._persona_eng: Optional[PersonaEngine] = None
        self._job_matcher: Optional[JobMatcher] = None
        self._learner: Optional[LearningRecommender] = None

    @property
    def exp_mgr(self) -> ExperienceManager:
        if self._exp_mgr is None:
            self._exp_mgr = ExperienceManager()
        return self._exp_mgr

    @property
    def persona_eng(self) -> PersonaEngine:
        if self._persona_eng is None:
            self._persona_eng = PersonaEngine()
        return self._persona_eng

    @property
    def job_matcher(self) -> JobMatcher:
        if self._job_matcher is None:
            self._job_matcher = JobMatcher()
        return self._job_matcher

    @property
    def learner(self) -> LearningRecommender:
        if self._learner is None:
            self._learner = LearningRecommender()
        return self._learner

    # ─── 经历 ───

    def get_experiences(self) -> List[Dict[str, Any]]:
        """获取经历列表"""
        try:
            exps = AsyncRunner.run(self.exp_mgr.list_by_user())
            return [self._exp_to_dict(e) for e in exps]
        except Exception as e:
            logger.error(f"get_experiences error: {e}")
            return []

    def save_experience(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """保存经历（绕过 draft 流程，直接保存）"""
        try:
            from src.services.experience_manager import ExperienceDraft
            draft = ExperienceDraft(
                raw_text=data.get("description", ""),
                extracted={
                    "title": data.get("title", ""),
                    "start_date": data.get("start_date", ""),
                    "end_date": data.get("end_date", ""),
                    "skills_demonstrated": data.get("skills", []),
                    "organization": data.get("company", ""),
                    "type": "work",
                },
            )
            result = AsyncRunner.run(self.exp_mgr.confirm_and_save(draft))
            return {"success": True, "id": str(result.id) if hasattr(result, "id") else ""}
        except Exception as e:
            logger.error(f"save_experience error: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def _exp_to_dict(exp: Any) -> Dict[str, Any]:
        return {
            "id": str(exp.id) if hasattr(exp, "id") else "",
            "title": getattr(exp, "title", ""),
            "description": getattr(exp, "description", ""),
            "company": getattr(exp, "company", ""),
            "role": getattr(exp, "role", ""),
            "start_date": str(getattr(exp, "start_date", "")),
            "end_date": str(getattr(exp, "end_date", "")),
            "skills": list(getattr(exp, "skills_demonstrated", []) or []),
            "status": getattr(exp, "status", "draft"),
        }

    # ─── 角色 ───

    def get_personas(self) -> List[Dict[str, Any]]:
        """获取角色列表"""
        try:
            personas = AsyncRunner.run(self.persona_eng.list_by_user())
            return [self._persona_to_dict(p) for p in personas]
        except Exception as e:
            logger.error(f"get_personas error: {e}")
            return []

    @staticmethod
    def _persona_to_dict(p: Any) -> Dict[str, Any]:
        return {
            "id": str(p.id) if hasattr(p, "id") else "",
            "name": getattr(p, "name", ""),
            "identity_statement": getattr(p, "identity_statement", ""),
            "tone_style": getattr(p, "tone_style", ""),
            "target_job_profiles": list(getattr(p, "target_job_profiles", []) or []),
        }

    # ─── 简历 ───

    def generate_resume(self, persona_id: str) -> Dict[str, Any]:
        """生成简历"""
        try:
            builder = ResumeBuilder(persona_id=persona_id)
            AsyncRunner.run(builder.prepare())
            md = AsyncRunner.run(builder.render(template_name="modern"))
            return {"success": True, "markdown": md}
        except Exception as e:
            logger.error(f"generate_resume error: {e}")
            return {"success": False, "error": str(e)}

    # ─── 岗位匹配 ───

    def match_job(self, jd_text: str) -> List[Dict[str, Any]]:
        """匹配岗位"""
        try:
            # 先解析 JD
            from src.services.job_parser import JobParser
            parser = JobParser()
            jd = AsyncRunner.run(parser.parse(jd_text))
            
            # 获取默认角色匹配
            personas = self.get_personas()
            if not personas:
                return []
            
            persona_id = personas[0].get("id", "")
            match = AsyncRunner.run(
                self.job_matcher.match(persona_id=persona_id, job_desc_id=str(jd.id) if hasattr(jd, "id") else "mock")
            )
            return [self._match_to_dict(match)] if match else []
        except Exception as e:
            logger.error(f"match_job error: {e}")
            return []

    @staticmethod
    def _match_to_dict(m: Any) -> Dict[str, Any]:
        return {
            "id": str(m.id) if hasattr(m, "id") else "",
            "score": getattr(m, "overall_score", 0),
            "skill_score": getattr(m, "skill_score", 0),
            "exp_score": getattr(m, "experience_score", 0),
            "matched_skills": list(getattr(m, "matched_skills", []) or []),
            "missing_skills": list(getattr(m, "missing_skills", []) or []),
        }

    # ─── 学习路径 ───

    def get_learning_path(self, skill: str) -> List[Dict[str, Any]]:
        """获取学习路径"""
        try:
            personas = self.get_personas()
            if not personas:
                return []
            persona_id = personas[0].get("id", "")
            items = AsyncRunner.run(
                self.learner.recommend_for_gap(
                    persona_id=persona_id,
                    missing_skills=[skill],
                )
            )
            return list(items or [])
        except Exception as e:
            logger.error(f"get_learning_path error: {e}")
            return []

    # ─── 统计 ───

    def get_stats(self) -> Dict[str, Any]:
        """获取欢迎页统计"""
        try:
            exps = self.get_experiences()
            personas = self.get_personas()
            return {
                "experiencesCount": len(exps),
                "personasCount": len(personas),
                "jobMatches": 0,  # TODO: 实现计数
                "learningPaths": 0,  # TODO: 实现计数
            }
        except Exception as e:
            logger.error(f"get_stats error: {e}")
            return {
                "experiencesCount": 0,
                "personasCount": 0,
                "jobMatches": 0,
                "learningPaths": 0,
            }
