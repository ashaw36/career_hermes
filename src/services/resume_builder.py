"""
CareerCraft Agent — 简历生成引擎

核心职责：根据角色档案筛选经历 → 排序 → 渲染模板 → 导出 Markdown/PDF。
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

from src.llm.router import LLMRouter
from src.models.entities import Experience, Persona, RoleExperienceWeight
from src.services.persona_engine import PersonaEngine


class ResumeBuilder:
    """
    简历生成引擎

    使用流程：
        builder = ResumeBuilder(persona_id="xxx")
        md = await builder.render(template_name="modern")
        builder.export_to_file(md, "/path/to/resume.md")
    """

    def __init__(self, persona_id: str, llm_router: Optional[LLMRouter] = None) -> None:
        self.persona_id = persona_id
        self.llm = llm_router or LLMRouter()
        self.persona_engine = PersonaEngine()
        self._persona: Optional[Persona] = None
        self._experiences: List[RoleExperienceWeight] = []

    async def prepare(self) -> "ResumeBuilder":
        """
        预处理：加载角色和筛选经历
        """
        self._persona = await self.persona_engine.get_by_id(self.persona_id)
        if not self._persona:
            raise ValueError(f"角色不存在: {self.persona_id}")

        # 计算并获取按 Fit Score 排序的经历
        await self.persona_engine.calculate_fit_scores(self.persona_id)
        self._experiences = await self.persona_engine.get_weighted_experiences(
            self.persona_id,
            min_score=0.0,
            limit=self._persona.max_experiences,
        )
        return self

    async def render(
        self,
        template_name: str = "modern",
        format: str = "markdown",
    ) -> str:
        """
        渲染简历

        Args:
            template_name: 模板名称（存放于 src/ui/templates/resume/）
            format: 输出格式，目前支持 "markdown"

        Returns:
            渲染后的文本
        """
        if not self._persona:
            await self.prepare()

        # 构建渲染上下文
        ctx = await self._build_context()

        # 加载模板
        template_dir = Path(__file__).parent.parent / "ui" / "templates" / "resume"
        env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(["html", "xml"]),
        )
        template = env.get_template(f"{template_name}.md.j2")

        return template.render(**ctx)

    async def _build_context(self) -> Dict[str, Any]:
        """构建 Jinja2 渲染上下文"""
        persona = self._persona
        assert persona is not None

        # 身份声明
        identity = persona.identity_statement or await self._generate_identity()

        # 职业叙事
        narrative = persona.career_narrative or ""

        # 经历列表
        exp_list = []
        for rew in self._experiences:
            exp = rew.experience
            exp_list.append({
                "title": exp.title,
                "organization": exp.organization,
                "type": exp.type,
                "period": self._format_period(exp.start_date, exp.end_date),
                "achievements": exp.structured_achievements or [],
                "skills": exp.skills_demonstrated or [],
                "metrics": exp.metrics or [],
                "relevance_score": rew.relevance_score,
            })

        return {
            "name": persona.name,
            "identity_statement": identity,
            "career_narrative": narrative,
            "tone_style": persona.tone_style,
            "experiences": exp_list,
            "generated_at": date.today().isoformat(),
        }

    async def _generate_identity(self) -> str:
        """
        使用 LLM 生成身份声明
        """
        if not self._experiences:
            return ""

        # 抽取关键信息
        exp_summaries = []
        for rew in self._experiences:
            exp = rew.experience
            exp_summaries.append(f"- {exp.title} @ {exp.organization}: {exp.raw_description[:100]}")

        prompt = f"""你是一个职业简历撰写专家。根据以下经历，生成一段1-2句的身份声明（Identity Statement）。

经历：
{chr(10).join(exp_summaries)}

角色侧重：{self._persona.tone_style if self._persona else 'business_insight'}

要求：
- 简洁有力，突出核心竞争力
- 不超过80个中文字符
- 不要套话

请直接返回身份声明文本，不要其他内容。
"""
        response = await self.llm.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
        )
        return response.strip() if isinstance(response, str) else ""

    def export_to_file(self, content: str, filepath: str) -> Path:
        """导出到文件"""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    @staticmethod
    def _format_period(start: Optional[date], end: Optional[date]) -> str:
        """格式化时间区间"""
        start_str = start.strftime("%Y.%m") if start else "?"
        end_str = end.strftime("%Y.%m") if end else "至今"
        return f"{start_str} — {end_str}"
