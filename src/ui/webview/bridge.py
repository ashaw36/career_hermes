"""
CareerCraft Agent — QWebChannel Python Bridge

通过 QWebChannel 向 JS 暴露后端 API，所有方法返回 JSON 字符串以便 JS 解析。
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QObject, Slot

from src.ui.webview.api_handler import CareerAPI

logger = logging.getLogger(__name__)


class CareerBridge(QObject):
    """
    QWebChannel 桥接对象

    JS 侧通过 window.pybridge 访问：
        window.pybridge.getExperiences((result) => { console.log(result); });
    """

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._api = CareerAPI()

    def _ok(self, data: Any) -> str:
        return json.dumps({"success": True, "data": data}, ensure_ascii=False)

    def _err(self, message: str) -> str:
        return json.dumps({"success": False, "error": message}, ensure_ascii=False)

    # ─── 经历 ───

    @Slot(result=str)
    def getExperiences(self) -> str:
        try:
            data = self._api.get_experiences()
            return self._ok(data)
        except Exception as e:
            logger.error(f"Bridge getExperiences error: {e}")
            return self._err(str(e))

    @Slot(str, result=str)
    def saveExperience(self, data_json: str) -> str:
        try:
            data: Dict[str, Any] = json.loads(data_json)
            result = self._api.save_experience(data)
            return json.dumps(result, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Bridge saveExperience error: {e}")
            return self._err(str(e))

    @Slot(str, result=str)
    def deleteExperience(self, exp_id: str) -> str:
        try:
            result = self._api.delete_experience(exp_id)
            return json.dumps(result, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Bridge deleteExperience error: {e}")
            return self._err(str(e))

    # ——— 角色 ———

    @Slot(result=str)
    def getPersonas(self) -> str:
        try:
            data = self._api.get_personas()
            return self._ok(data)
        except Exception as e:
            logger.error(f"Bridge getPersonas error: {e}")
            return self._err(str(e))

    @Slot(str, result=str)
    def getPersonaById(self, persona_id: str) -> str:
        try:
            data = self._api.get_persona_by_id(persona_id)
            if data is None:
                return self._err("角色不存在")
            return self._ok(data)
        except Exception as e:
            logger.error(f"Bridge getPersonaById error: {e}")
            return self._err(str(e))

    @Slot(str, result=str)
    def createPersona(self, data_json: str) -> str:
        try:
            data: Dict[str, Any] = json.loads(data_json)
            result = self._api.create_persona(data)
            return json.dumps(result, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Bridge createPersona error: {e}")
            return self._err(str(e))

    @Slot(str, str, result=str)
    def updatePersona(self, persona_id: str, data_json: str) -> str:
        try:
            data: Dict[str, Any] = json.loads(data_json)
            result = self._api.update_persona(persona_id, data)
            return json.dumps(result, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Bridge updatePersona error: {e}")
            return self._err(str(e))

    @Slot(str, result=str)
    def deletePersona(self, persona_id: str) -> str:
        try:
            result = self._api.delete_persona(persona_id)
            return json.dumps(result, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Bridge deletePersona error: {e}")
            return self._err(str(e))

    # ─── 简历 ───

    @Slot(str, result=str)
    def generateResume(self, persona_id: str) -> str:
        try:
            result = self._api.generate_resume(persona_id)
            return json.dumps(result, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Bridge generateResume error: {e}")
            return self._err(str(e))

    # ─── 岗位匹配 ───

    @Slot(str, result=str)
    def parseJD(self, jd_text: str) -> str:
        try:
            result = self._api.parse_jd(jd_text)
            return json.dumps(result, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Bridge parseJD error: {e}")
            return self._err(str(e))

    @Slot(str, str, result=str)
    def matchJob(self, job_desc_id: str, persona_id: str) -> str:
        try:
            result = self._api.match_job(job_desc_id, persona_id)
            return json.dumps(result, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Bridge matchJob error: {e}")
            return self._err(str(e))

    @Slot(result=str)
    def listJobs(self) -> str:
        try:
            data = self._api.list_jobs()
            return self._ok(data)
        except Exception as e:
            logger.error(f"Bridge listJobs error: {e}")
            return self._err(str(e))

    @Slot(str, result=str)
    def deleteJob(self, job_desc_id: str) -> str:
        try:
            result = self._api.delete_job(job_desc_id)
            return json.dumps(result, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Bridge deleteJob error: {e}")
            return self._err(str(e))

    @Slot(str, result=str)
    def getJobMatches(self, job_desc_id: str) -> str:
        try:
            result = self._api.get_job_matches(job_desc_id)
            return json.dumps(result, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Bridge getJobMatches error: {e}")
            return self._err(str(e))

    @Slot(str, str, result=str)
    def updateMatchStatus(self, match_id: str, status: str) -> str:
        try:
            result = self._api.update_match_status(match_id, status)
            return json.dumps(result, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Bridge updateMatchStatus error: {e}")
            return self._err(str(e))

    @Slot(str, result=str)
    def reframeResume(self, match_id: str) -> str:
        try:
            result = self._api.reframe_resume(match_id)
            return json.dumps(result, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Bridge reframeResume error: {e}")
            return self._err(str(e))

    @Slot(str, result=str)
    def getReframeResults(self, match_id: str) -> str:
        try:
            result = self._api.get_reframe_results(match_id)
            return json.dumps(result, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Bridge getReframeResults error: {e}")
            return self._err(str(e))

    # ─── 学习路径 ───

    @Slot(str, result=str)
    def getLearningPath(self, skill: str) -> str:
        try:
            data = self._api.get_learning_path(skill)
            return self._ok(data)
        except Exception as e:
            logger.error(f"Bridge getLearningPath error: {e}")
            return self._err(str(e))

    # ─── 统计 ───

    @Slot(result=str)
    def getStats(self) -> str:
        try:
            data = self._api.get_stats()
            return self._ok(data)
        except Exception as e:
            logger.error(f"Bridge getStats error: {e}")
            return self._err(str(e))
