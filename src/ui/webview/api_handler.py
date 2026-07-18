"""
CareerCraft Agent — WebView API 同步适配层

将异步 Service 封装为同步 API，供 QWebChannel Bridge 调用。
在后台线程中运行 async 代码，避免与 Qt 主事件循环冲突。
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from concurrent.futures import TimeoutError as FutureTimeoutError
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional

from sqlalchemy import func, select

from src.models.database import AsyncSessionLocal
from src.models.entities import JobMatch, LearningPath
from src.services.experience_manager import ExperienceManager
from src.services.job_matcher import JobMatcher
from src.services.learning_recommender import LearningRecommender
from src.services.persona_engine import PersonaEngine
from src.services.resume_builder import ResumeBuilder

logger = logging.getLogger(__name__)


class AsyncRunnerTimeoutError(TimeoutError):
    """Raised when a synchronous webview API wait exceeds its timeout."""


class AsyncRunner:
    """在独立线程中运行 async 协程，返回同步结果"""

    _executor: Optional[ThreadPoolExecutor] = None
    _default_timeout: float = float(os.getenv("CC_ASYNC_RUNNER_TIMEOUT_SECONDS", "60"))

    @classmethod
    def _get_executor(cls) -> ThreadPoolExecutor:
        if cls._executor is None:
            cls._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="career_async")
        return cls._executor

    @classmethod
    def run(cls, coro: Any, timeout: Optional[float] = None) -> Any:
        """提交协程到后台线程执行，阻塞等待结果"""
        def _run() -> Any:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(coro)
            finally:
                loop.close()

        future = cls._get_executor().submit(_run)
        effective_timeout = timeout if timeout is not None else cls._default_timeout
        try:
            return future.result(timeout=effective_timeout)
        except FutureTimeoutError as exc:
            future.cancel()
            raise AsyncRunnerTimeoutError(
                f"操作超时：后台任务在 {effective_timeout:.0f} 秒内未完成，请稍后重试或检查 LLM/网络配置。"
            ) from exc


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
            exp_id = str(data.get("id") or "").strip()
            fields: Dict[str, Any] = {
                "title": data.get("title", ""),
                "organization": data.get("organization") or data.get("company", ""),
                "type": data.get("type", "work"),
                "start_date": self.exp_mgr._parse_date(data.get("start_date")),
                "end_date": self.exp_mgr._parse_date(data.get("end_date")),
                "raw_description": data.get("raw_description") or data.get("description", ""),
                "skills_demonstrated": data.get("skills_demonstrated") or data.get("skills", []),
                "structured_achievements": data.get("structured_achievements")
                or data.get("achievements"),
            }
            if exp_id:
                result = AsyncRunner.run(self.exp_mgr.update(exp_id, **fields))
                if result is None:
                    return {"success": False, "error": f"经历不存在或无法更新: {exp_id}"}
                return {"success": True, "id": str(result.id)}

            from src.services.experience_manager import ExperienceDraft
            draft = ExperienceDraft(
                raw_text=fields["raw_description"],
                extracted={
                    "title": fields["title"],
                    "start_date": data.get("start_date", ""),
                    "end_date": data.get("end_date", ""),
                    "skills_demonstrated": fields["skills_demonstrated"],
                    "structured_achievements": fields["structured_achievements"],
                    "organization": fields["organization"],
                    "type": fields["type"],
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
            "description": getattr(exp, "raw_description", ""),
            "company": getattr(exp, "organization", ""),
            "role": getattr(exp, "title", ""),
            "type": getattr(exp, "type", "work"),
            "start_date": str(getattr(exp, "start_date", "")),
            "end_date": str(getattr(exp, "end_date", "")),
            "skills": list(getattr(exp, "skills_demonstrated", []) or []),
            "achievements": list(getattr(exp, "structured_achievements", []) or []),
            "metrics": list(getattr(exp, "metrics", []) or []),
            "status": getattr(exp, "status", "draft"),
            "version": getattr(exp, "version", 1),
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
            "career_narrative": getattr(p, "career_narrative", ""),
            "tone_style": getattr(p, "tone_style", ""),
            "capability_weights": dict(getattr(p, "capability_weights", {}) or {}),
            "target_job_profiles": list(getattr(p, "target_job_profiles", []) or []),
            "max_experiences": getattr(p, "max_experiences", 5),
            "preferred_model": getattr(p, "preferred_model", ""),
            "is_default": getattr(p, "is_default", False),
        }

    # ─── 简历 ───

    def generate_resume(self, persona_id: str, template_name: str = "modern") -> Dict[str, Any]:
        """生成简历"""
        try:
            builder = ResumeBuilder(persona_id=persona_id)
            AsyncRunner.run(builder.prepare())
            md = AsyncRunner.run(builder.render(template_name=template_name))
            return {"success": True, "markdown": md}
        except Exception as e:
            logger.error(f"generate_resume error: {e}")
            return {"success": False, "error": str(e)}

    # ─── 岗位匹配 ───

    def match_job(self, jd_text: str) -> List[Dict[str, Any]]:
        """匹配岗位"""
        try:
            # 先解析并保存 JD
            from src.services.job_parser import JobParser
            parser = JobParser()
            jd = AsyncRunner.run(parser.parse_and_save(jd_text, source="manual"))
            
            # 获取默认角色匹配
            personas = self.get_personas()
            if not personas:
                return []
            
            persona_id = personas[0].get("id", "")
            match = AsyncRunner.run(
                self.job_matcher.match(persona_id=persona_id, job_desc_id=str(jd.id))
            )
            return [self._match_to_dict(match)] if match else []
        except Exception as e:
            logger.error(f"match_job error: {e}")
            return []

    @staticmethod
    def _match_to_dict(m: Any) -> Dict[str, Any]:
        breakdown = getattr(m, "score_breakdown", {}) or {}
        return {
            "id": str(m.id) if hasattr(m, "id") else "",
            "persona_id": str(getattr(m, "persona_id", "")) or "",
            "job_desc_id": str(getattr(m, "job_desc_id", "")) or "",
            "score": getattr(m, "match_score", 0),
            "skill_score": breakdown.get("skill", 0),
            "exp_score": breakdown.get("experience", 0),
            "score_breakdown": dict(breakdown),
            "matched_skills": list(getattr(m, "matched_skills", []) or []),
            "missing_skills": list(getattr(m, "missing_skills", []) or []),
            "tracking_status": getattr(m, "tracking_status", "new"),
            "notes": getattr(m, "notes", ""),
            "ai_analysis": getattr(m, "ai_analysis", ""),
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
            counts = AsyncRunner.run(self._get_db_counts())
            return {
                "experiencesCount": len(exps),
                "personasCount": len(personas),
                "jobMatches": counts["jobMatches"],
                "learningPaths": counts["learningPaths"],
            }
        except Exception as e:
            logger.error(f"get_stats error: {e}")
            return {
                "experiencesCount": 0,
                "personasCount": 0,
                "jobMatches": 0,
                "learningPaths": 0,
            }

    @staticmethod
    async def _get_db_counts() -> Dict[str, int]:
        async with AsyncSessionLocal() as session:
            job_matches = await session.scalar(select(func.count()).select_from(JobMatch))
            learning_paths = await session.scalar(select(func.count()).select_from(LearningPath))
            return {
                "jobMatches": int(job_matches or 0),
                "learningPaths": int(learning_paths or 0),
            }
