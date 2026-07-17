"""
CareerCraft Agent — 岗位匹配服务

核心职责：比较角色档案 + 经历 vs JD，计算综合匹配度分数（0-100），
分析匹配/缺失技能，存入 JobMatch 模型。
Sprint 4 核心服务之三。
"""

from __future__ import annotations

import logging
import re
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select

from src.models.database import AsyncSessionLocal
from src.models.entities import Experience, JobDesc, JobMatch, Persona

logger = logging.getLogger(__name__)


class JobMatchError(Exception):
    """岗位匹配异常基类"""

    def __init__(self, message: str, persona_id: str = "", job_desc_id: str = "") -> None:
        super().__init__(message)
        self.persona_id = persona_id
        self.job_desc_id = job_desc_id


class JobMatcher:
    """
    岗位匹配器

    使用流程：
        matcher = JobMatcher()
        match = await matcher.match(persona_id="xxx", job_desc_id="yyy")
        report = await matcher.get_match_report(match.id)
    """

    # 允许的投递状态
    _VALID_STATUSES = {
        "new",
        "interested",
        "applied",
        "interviewing",
        "offered",
        "rejected",
        "ghosted",
        "accepted",
        "declined",
    }

    async def match(self, persona_id: str, job_desc_id: str) -> JobMatch:
        """
        计算匹配度并保存 JobMatch。

        算法（纯规则，无 LLM）：
        1. 技能匹配度 = (匹配技能数 / JD 技能总数) * 60
        2. 经验匹配度 = 根据经历总年限是否满足 JD 要求，0-30 分
        3. 其他匹配度 = 学历/地点匹配，0-10 分
        4. 总分 = min(100, 技能度 + 经验度 + 其他度)
        """
        async with AsyncSessionLocal() as session:
            # 加载角色
            persona_result = await session.execute(
                select(Persona).where(Persona.id == persona_id)
            )
            persona = persona_result.scalar_one_or_none()
            if not persona:
                raise JobMatchError(f"角色不存在: {persona_id}", persona_id=persona_id)

            # 加载 JD
            job_result = await session.execute(
                select(JobDesc).where(JobDesc.id == job_desc_id)
            )
            job_desc = job_result.scalar_one_or_none()
            if not job_desc:
                raise JobMatchError(
                    f"岗位描述不存在: {job_desc_id}", job_desc_id=job_desc_id
                )

            # 加载角色的所有确认经历
            exp_result = await session.execute(
                select(Experience).where(
                    Experience.user_id == persona.user_id,
                    Experience.status == "confirmed",
                )
            )
            experiences = list(exp_result.scalars().all())

            # 从角色的 capability_weights 提取技能列表
            persona_skills = list((persona.capability_weights or {}).keys())
            job_skills = job_desc.parsed_skills or []

            # 计算各项分数
            matched, missing, skill_score = self._calculate_skill_match(
                persona_skills, job_skills
            )
            exp_score = self._calculate_experience_match(experiences, job_desc)
            other_score = self._calculate_other_match(persona, job_desc)

            total = min(100.0, skill_score + exp_score + other_score)

            breakdown: Dict[str, float] = {
                "skill": round(skill_score, 2),
                "experience": round(exp_score, 2),
                "other": round(other_score, 2),
            }

            # 检查是否已有匹配记录，有则更新
            existing_result = await session.execute(
                select(JobMatch).where(
                    JobMatch.persona_id == persona_id,
                    JobMatch.job_desc_id == job_desc_id,
                )
            )
            existing = existing_result.scalar_one_or_none()

            if existing:
                existing.match_score = int(total)
                existing.matched_skills = matched
                existing.missing_skills = missing
                existing.score_breakdown = breakdown
                await session.commit()
                await session.refresh(existing)
                logger.info(
                    "JobMatch 已更新: id=%s score=%s",
                    existing.id,
                    existing.match_score,
                )
                return existing

            match = JobMatch(
                persona_id=persona_id,
                job_desc_id=job_desc_id,
                match_score=int(total),
                matched_skills=matched,
                missing_skills=missing,
                score_breakdown=breakdown,
                ai_analysis="",
                tracking_status="new",
            )
            session.add(match)
            await session.commit()
            await session.refresh(match)
            logger.info(
                "JobMatch 已创建: id=%s score=%s",
                match.id,
                match.match_score,
            )
            return match

    @staticmethod
    def _calculate_skill_match(
        persona_skills: List[str], job_skills: List[str]
    ) -> Tuple[List[str], List[str], float]:
        """
        计算技能匹配度。

        Returns:
            (matched_skills, missing_skills, score_0_to_60)
        """
        if not job_skills:
            return [], [], 30.0  # JD 无技能要求，给中等分

        persona_skills_lower = [s.lower().strip() for s in persona_skills]
        matched = []
        missing = []

        for skill in job_skills:
            skill_lower = skill.lower().strip()
            if skill_lower in persona_skills_lower:
                matched.append(skill)
            else:
                # 子串宽松匹配
                found = any(
                    skill_lower in ps or ps in skill_lower
                    for ps in persona_skills_lower
                )
                if found:
                    matched.append(skill)
                else:
                    missing.append(skill)

        score = (len(matched) / len(job_skills)) * 60.0
        return matched, missing, score

    @staticmethod
    def _calculate_experience_match(
        experiences: List[Experience], job_desc: JobDesc
    ) -> float:
        """
        计算经验匹配度（0-30分）。
        根据经历总年限与 JD 要求比较。
        """
        required_years = JobMatcher._parse_years_requirement(
            job_desc.years_of_experience
        )
        if required_years <= 0:
            return 30.0  # 无明确要求，给满分

        total_years = JobMatcher._calculate_total_years(experiences)
        if total_years >= required_years:
            return 30.0

        pct = total_years / required_years
        return pct * 30.0

    @staticmethod
    def _calculate_other_match(persona: Persona, job_desc: JobDesc) -> float:
        """
        其他匹配度（0-10分）：学历 + 地点。
        """
        score = 0.0

        # 学历匹配（5分）
        edu_requirement = job_desc.education_requirement or ""
        if edu_requirement:
            # 简化匹配：如果 JD 有学历要求但角色无学历信息，给 3 分中立
            score += 3.0
        else:
            score += 5.0  # 无学历要求，给满分

        # 地点匹配（5分）
        if job_desc.location and persona.target_job_profiles:
            # 检查目标岗位列表中是否包含该地点
            target_str = " ".join(persona.target_job_profiles).lower()
            if job_desc.location.lower() in target_str:
                score += 5.0
            else:
                score += 2.5
        else:
            score += 5.0  # 无地点要求，给满分

        return min(10.0, score)

    @staticmethod
    def _parse_years_requirement(years_str: Optional[str]) -> float:
        """
        解析工作年限字符串，返回最小要求年数。

        支持格式："3-5年"、"5年以上"、"3年及以上"、"1-3 年"、"3年+"
        """
        if not years_str:
            return 0.0

        text = years_str.strip()
        # 提取数字
        numbers = re.findall(r"\d+", text)
        if not numbers:
            return 0.0

        nums = [int(n) for n in numbers]

        # 如果有两个数字，取范围下限
        if len(nums) >= 2:
            return float(min(nums))

        # 只有一个数字
        return float(nums[0])

    @staticmethod
    def _calculate_total_years(experiences: List[Experience]) -> float:
        """
        计算经历总年限（去重叠）。

        简化算法：计算每段经历的时长，加总。
        """
        total_months = 0
        today = date.today()

        for exp in experiences:
            start = exp.start_date
            end = exp.end_date or today
            if not start:
                continue
            if end < start:
                continue
            # 计算月份差
            months = (end.year - start.year) * 12 + (end.month - start.month)
            total_months += max(0, months)

        return total_months / 12.0

    async def get_match_report(self, match_id: str) -> str:
        """
        获取匹配报告。
        """
        async with AsyncSessionLocal() as session:
            match = await session.get(JobMatch, match_id)
            if not match:
                return f"未找到匹配记录: {match_id}"

            lines = [
                f"## 岗位匹配报告",
                f"",
                f"- 匹配 ID: {match.id}",
                f"- 角色 ID: {match.persona_id}",
                f"- 岗位 ID: {match.job_desc_id}",
                f"- **综合匹配度: {match.match_score}/100**",
                f"",
                f"### 分项得分",
                f"- 技能匹配: {match.score_breakdown.get('skill', 0)} / 60",
                f"- 经验匹配: {match.score_breakdown.get('experience', 0)} / 30",
                f"- 其他匹配: {match.score_breakdown.get('other', 0)} / 10",
                f"",
                f"### 匹配技能 ({len(match.matched_skills or [])} 个)",
            ]
            for skill in match.matched_skills or []:
                lines.append(f"- ✅ {skill}")

            lines.extend([
                f"",
                f"### 缺失技能 ({len(match.missing_skills or [])} 个)",
            ])
            for skill in match.missing_skills or []:
                lines.append(f"- ❌ {skill}")

            lines.extend([
                f"",
                f"### 投递状态",
                f"{match.tracking_status}",
            ])

            if match.ai_analysis:
                lines.extend([f"", f"### AI 分析", f"{match.ai_analysis}"])

            return "\n".join(lines)

    async def list_matches(self, persona_id: str) -> List[JobMatch]:
        """
        列出角色的所有匹配记录，按匹配度倒序。
        """
        async with AsyncSessionLocal() as session:
            stmt = (
                select(JobMatch)
                .where(JobMatch.persona_id == persona_id)
                .order_by(JobMatch.match_score.desc())
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def update_tracking_status(
        self, match_id: str, status: str
    ) -> Optional[JobMatch]:
        """
        更新投递状态。
        """
        if status not in self._VALID_STATUSES:
            logger.warning("无效的投递状态: %s", status)
            return None

        async with AsyncSessionLocal() as session:
            match = await session.get(JobMatch, match_id)
            if not match:
                return None

            match.tracking_status = status
            await session.commit()
            await session.refresh(match)
            logger.info("JobMatch 状态已更新: id=%s status=%s", match_id, status)
            return match

    async def delete_match(self, match_id: str) -> bool:
        """删除匹配记录（硬删除）〄"""
        async with AsyncSessionLocal() as session:
            match = await session.get(JobMatch, match_id)
            if not match:
                return False
            await session.delete(match)
            await session.commit()
            logger.info("JobMatch 已删除: id=%s", match_id)
            return True
