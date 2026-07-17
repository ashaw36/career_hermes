# Batch 1 — Sprint 4 剩余 + 测试验证

你是 CareerCraft Agent 项目的后端工程师。代码规范：Python 3.11，禁用PEP 585内置泛型，必须使用 typing.List/typing.Dict/typing.Optional等；所有中文必须直接使用UTF-8明文，严禁\uXXXX转义。

## Task 1.1: 创建 src/services/job_matcher.py

职责：比较角色档案 + 经历 vs JD，计算综合匹配度分数（0-100），分析匹配/缺失技能，存入 JobMatch 模型。

需要先阅读 src/models/entities.py 了解 JobMatch 字段：
- match_score: int (0-100)
- matched_skills: List[str]
- missing_skills: List[str]
- score_breakdown: dict
- ai_analysis: str
- tracking_status: str

核心方法：
- `match(persona_id, job_desc_id)` → 计算匹配度并保存 JobMatch，返回 JobMatch
- `_calculate_skill_match(persona_skills, job_skills)` → 返回 (matched, missing, score)
- `_calculate_experience_match(experiences, job_desc)` → 经验年限/领域匹配度分数
- `get_match_report(match_id)` → 返回详细报告字符串
- `list_matches(persona_id)` → 列出角色的所有匹配记录
- `update_tracking_status(match_id, status)` → 更新投递状态

匹配度计算算法（不使用LLM，纯规则）：
1. 技能匹配度 = (匹配技能数 / JD技能总数) * 60 分
2. 经验匹配度 = 根据经历年限是否满足JD要求，0-30分
3. 教育/地点等其他 = 0-10分（简化）
4. 总分 = min(100, 技能度 + 经验度 + 其他度)

## Task 1.2: 修改 src/llm/router.py 添加多模型容错

当前 `_resolve_provider()` 只返回默认供应商。修改 `chat()` 方法使其内部自动尝试 fallback：
- 失败时（LLMTimeoutError / LLMRateLimitError / httpx.HTTPStatusError）自动遍历下一个 enabled 的供应商
- 记录降级日志
- 所有供应商都失败才抛出错误

修改方式：在现有 chat() 方法内部将主调用逻辑抽取为 `_chat_single_provider()`，然后 chat() 循环尝试多个供应商。

## Task 1.3: 运行测试

执行：pytest tests/ -v --tb=short
修复所有报错。如果 tests/conftest.py 中的内存数据库配置有问题（比如 Base 导入路径不对），请修复。

最后提交 git commit -m "feat(sprint4): job_matcher + 多模型容错 + 测试修复"
