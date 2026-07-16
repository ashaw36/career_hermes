# CareerCraft Agent — 项目单点入口

> 基于 BMad 框架开发 | 个人职业智能体 | 角色档案驱动

## 🔒 已锁定决策（Decision Lock）

| 决策 | 选择 | 不可逆理由 |
|------|------|-----------|
| **D1 — 产品形态** | B. 桌面应用（本地 GUI）| 个人自用工具，数据本地化优先，无需服务端部署 |
| **D2 — 目标用户** | A. 个人自用 | MVP 阶段只服务单一用户，架构预留多用户扩展口 |
| **D3 — 数据来源** | 简历自动生成(A) + 岗位爬虫(B) + 学习素材实时搜索(B) | 经历库从0构建，岗位信息依赖爬虫，学习素材基于技能 Gap 动态检索 |

## 📋 项目全景

CareerCraft Agent 是一个**角色档案驱动的个人职业智能体**，核心链路：

```
个人经历录入 → 角色档案配置 → 简历自动生成 → 岗位智能匹配 → 技能 Gap 分析 → 学习路径推荐 → 能力提升追踪
```

### 核心特性
- **多角色档案**：同一套经历库，可切换 AI PM / 销售 / 架构师等角色，生成对应简历和岗位匹配
- **对话式调整**：目标岗位、角色侧重均可通过自然对话动态调整
- **多模型切换**：支持通义千问、OpenAI、Claude 等多种 LLM 后端
- **本地优先**：数据存储在本地 SQLite，个人隐私可控

## 🗂️ 文档导航

### 稳定知识树 `docs/`
- `architecture/` — 系统级技术规范
- `decisions/` — ADR 架构决策记录
- `modules/{module}/` — 模块级三件套（AGENTS.md + design/ + interfaces/）

### 过程产物树 `_bmad-output/`
- `planning-artifacts/` — PRD、架构设计、Epics
- `implementation-artifacts/` — Sprint Plan、Story、Review 报告

### 源代码 `src/`
- `core/` — 核心引擎（LLM 路由、配置管理）
- `models/` — 数据模型（SQLAlchemy）
- `services/` — 业务服务层
- `api/` — 内部 API / 桌面端通信
- `ui/` — 桌面 GUI（PySide6）
- `agents/` — 智能体工作流
- `crawler/` — 招聘网站爬虫
- `utils/` — 工具函数

## 📅 开发节奏

| 阶段 | 状态 | 交付物 |
|------|------|--------|
| Phase 1 — 分析 | 🔄 进行中 | 竞品调研、技术预研、需求分析 |
| Phase 2 — 规划 | ⏳ 待启动 | PRD 需求文档 |
| Phase 3 — 方案 | ⏳ 待启动 | Architecture + Epics + 就绪检查 |
| Phase 4 — 实施 | ⏳ 待启动 | Sprint Plan → Story → Dev → Review |

## 📌 Notion 映射

- 母页面：[hermes信息收集](https://www.notion.so/3691bfd6-d4a8-8075-b435-ec4385b4bb73)
- 备份命名：`YYYY-MM-DD_标题.md`

## 🚀 快速启动

```bash
cd /mnt/d/workplace_for_hermes/career-agent
# 待补充
```

## 📝 变更日志

- 2026-07-17 — 项目初始化，BMAD 骨架搭建，Phase 1 启动
