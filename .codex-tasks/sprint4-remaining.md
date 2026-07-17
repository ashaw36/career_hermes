# Codex Task — Sprint 4 剩余 + Sprint 5 + Sprint 6

## 项目路径
/mnt/d/workplace_for_hermes/career-agent/

## 代码规范
- Python 3.11，禁用 PEP 585 内置泛型，必须使用 typing.List, typing.Dict, typing.Optional 等
- 所有中文输出必须直接使用 UTF-8 明文，严禁 \uXXXX 转义
- 异步代码使用 asyncio + SQLAlchemy 2.0 AsyncSession

## Task 1: 创建 job_matcher.py

文件：`src/services/job_matcher.py`

职责：比较角色档案 + 经历 vs JD，计算综合匹配度分数（0-100），分析匹配/缺失技能，存入 JobMatch 模型。

核心方法：
- `match(persona_id, job_desc_id)` → 计算匹配度并保存 JobMatch
- `_calculate_skill_match(persona_skills, job_skills)` → 技能交集/差集
- `_calculate_experience_match(experiences, job_desc)` → 经验年限/领域匹配
- `get_match_report(match_id)` → 返回详细匹配报告

需读取 `src/models/entities.py` 中的 JobMatch 字段，确保兼容。

## Task 2: router.py 多模型容错

修改 `src/llm/router.py`：

当前 `_resolve_provider()` 只返回默认供应商。新增 `chat_with_fallback()` 方法：
- 先尝试默认供应商
- 失败时（超时/限流/HTTP错误）自动遍历下一个 enabled 的供应商
- 记录降级日志
- 所有供应商都失败才抛出 LLMError

同时修改现有 `chat()` 方法内部也集成 fallback 逻辑。

## Task 3: 运行测试

```bash
cd /mnt/d/workplace_for_hermes/career-agent
pytest tests/ -v --tb=short
```

修复所有报错。注意 `tests/conftest.py` 使用了内存数据库 `sqlite+aiosqlite:///:memory:`，需要确保 `src/models/database.py` 中的 Base 可以被导入。

## Task 4: Sprint 5 — 学习路径推荐

创建 `src/services/learning_recommender.py`：
- `recommend_for_gap(persona_id, missing_skills)` → 根据缺失技能生成学习路径
- `create_learning_path(persona_id, target_gap, items)` → 保存到 LearningPath 表
- `get_active_paths(persona_id)` → 获取进行中的学习路径

items 结构示例：`[{ "type": "course", "title": "...", "source": "...", "estimated_hours": 10, "priority": 1 }]`

Prompt 文件：`src/llm/prompts/learning_recommendation.py`

## Task 5: Sprint 6 — GUI 岗位匹配页

创建 `src/ui/pages/job_match_page.py`：
- 左侧：JD 列表（从 JobDesc 表加载）
- 右侧：选中 JD 后显示匹配度分析（调用 JobMatcher）
- 顶部：角色选择下拉框
- 功能：粘贴 JD → 解析 → 匹配计算 → 显示匹配分数 + 匹配/缺失技能 + AI 分析

修改 `src/ui/main_window.py` 添加导航入口。

## Task 6: 创建测试补充

为新增服务（job_matcher, learning_recommender）创建测试文件。

## 验收标准
- [ ] `pytest tests/ -v` 全部通过
- [ ] `python -c "import src.services.job_matcher; import src.services.learning_recommender"` 无报错
- [ ] `python -m py_compile src/ui/pages/job_match_page.py` 通过
