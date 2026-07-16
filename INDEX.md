# CareerCraft Agent — 项目单点入口

> 基于 BMad 框架开发 | 个人职业智能体 | 角色档案驱动

## 🔒 已锁定决策（Decision Lock）

| 决策 | 选择 | 不可逆理由 |
|------|------|-----------|
| **D1 — 产品形态** | B. 桌面应用（PySide6 GUI）| 个人自用工具，数据本地化优先，无需服务端部署 |
| **D2 — 目标用户** | A. 个人自用 | MVP 只服务单一用户，架构预留多用户扩展口 |
| **D3 — 数据来源** | 简历A + 岗位爬虫B + 学习素材B | 经历库从0构建，岗位依赖Playwright爬虫，学习素材基于Gap动态检索 |
| **D4 — LLM策略** | 通义千问为主，支持多模型切换 | 通义千问API已确认可用，成本低、中文效果好 |
| **D5 — 角色引擎** | 规则+Prompt混合方案 | 个人工具需可解释性和可控性，规则引擎保留用户干预能力 |

## 📋 项目全景

CareerCraft Agent 是一个**角色档案驱动的个人职业智能体**，运行于本地桌面。

```
个人经历录入 → 角色档案配置 → 简历自动生成 → 岗位智能匹配 → 技能 Gap 分析 → 学习路径推荐 → 能力提升追踪
```

### 核心特性
- **多角色档案**：同一套经历库，切换 AI PM / 销售 / 架构师等角色，生成对应简历和岗位匹配
- **对话式调整**：目标岗位、角色侧重均可通过自然语言动态调整
- **多模型切换**：支持通义千问、OpenAI、Claude 等多种 LLM 后端，自动降级
- **本地优先**：数据存储在本地 SQLite，API Key 加密保存，隐私可控

## 📅 开发进度

| 阶段 | 状态 | 交付物 |
|------|------|--------|
| **Phase 1 — 分析** | ✅ 已完成 | 市场调研、技术预研、需求分析 |
| **Phase 2 — 规划** | ✅ 已完成 | PRD v1.0（含P0/P1/P2、验收标准、用户旅程） |
| **Phase 3 — 方案** | ✅ 已完成 | 架构设计 v1.0、Epic/Story 拆分、就绪检查 |
| **Sprint 1 (Week 1-2)** | ✅ 已完成 | 项目骨架、数据库ORM、LLM路由、安全存储 |
| **Sprint 2 (Week 3-4)** | ✅ 核心代码完成 | 经历管理服务、角色引擎、Fit Score 计算 |
| Sprint 3 (Week 5-6) | 🔄 待启动 | 智能录入、简历渲染 |
| Sprint 4 (Week 7-8) | ⏳ 待启动 | 经历重述、多模型、JD解析 |
| Sprint 5 (Week 9-10) | ⏳ 待启动 | 岗位匹配、Gap可视化、学习推荐 |
| Sprint 6 (Week 11-12) | ⏳ 待启动 | Polish、测试、打包、文档 |

## 📁 核心文件清单

### 稳定知识树 `docs/`
| 路径 | 说明 |
|-------|------|
| `_bmad-output/planning-artifacts/prd/PRD_v1.0.md` | 需求文档 |
| `_bmad-output/planning-artifacts/architecture/ARCH_v1.0.md` | 架构设计 |
| `_bmad-output/planning-artifacts/epics/EPICS_v1.0.md` | Epic/Story 拆分 |
| `_bmad-output/planning-artifacts/phase1/` | Phase 1 三份调研报告 |

### 源代码 `src/`
| 路径 | 行数 | 说明 |
|-------|------|------|
| `src/models/entities.py` | 235 | 7张核心ORM表（Experience/Persona/SkillNode/JobDesc/JobMatch/LearningPath/RoleExperienceWeight） |
| `src/models/database.py` | 70 | 异步SQLite引擎、WAL模式、会话管理 |
| `src/config/settings.py` | 154 | Pydantic Settings + YAML配置 + 多模型LLM供应商配置 |
| `src/llm/router.py` | 205 | LLM路由器，支持流式/非流式、超时、降级 |
| `src/services/experience_manager.py` | 230 | 经历CRUD、对话式录入、时间冲突检测、草稿状态机 |
| `src/services/persona_engine.py` | 230 | 角色CRUD、Fit Score计算（关键词×权重）、经历筛选排序 |
| `src/utils/security.py` | 170 | API Key加密存储（keyring/Fernet）、主密码派生 |
| `src/ui/main_window.py` | 163 | PySide6主窗口骨架、页面导航、全局异常处理 |
| `src/main.py` | 41 | 应用入口（数据库初始化 → GUI启动） |

**~~总代码量：~1,500行~~**

## 📁 Git 提交历史

| Commit | 说明 |
|--------|------|
| `d3cfa85` | Sprint 1: 项目骨架 + 数据库ORM + LLM路由 + 安全存储 |
| `8b4e6b8` | Sprint 2: 经历管理服务 + 角色引擎 + Fit Score 计算 |

## 📋 Notion 映射

- 母页面：[hermes信息收集](https://www.notion.so/3691bfd6-d4a8-8075-b435-ec4385b4bb73)
- 备命名格式：`YYYY-MM-DD_标题.md`

## 🚀 快速启动

```bash
cd /mnt/d/workplace_for_hermes/career-agent
source .venv/bin/activate
python -m src.main
```

## 📝 变更日志

- **2026-07-17** — 项目初始化，BMAD 骨架搭建，Phase 1-3 完成，Sprint 1-2 核心代码落地
