# 参与贡献

感谢你对 WhatIf 的关注！我们欢迎各种形式的贡献 —— 报告 Bug、提出建议、改进文档或提交代码。

AI 辅助的 PR 同样欢迎。

---

> **目录**
>
> [报告 Bug](#报告-bug) · [请求新功能](#请求新功能) · [提交代码](#提交代码) · [开发环境搭建](#开发环境搭建) · [代码风格](#代码风格) · [扩展指南](#扩展指南)

---

## 报告 Bug

请请通过 [Bug 报告](https://github.com/ypcypc/WhatIf/issues/new?template=bug_report.md) 提交 Issue。

**一份好的 Bug 报告应该包含：**

1. **复现步骤** — 按步骤描述，让其他人能重现你的问题
2. **期望 vs 实际行为** — 你期望发生什么，实际发生了什么
3. **环境信息** — 操作系统、Python/Node.js 版本、使用的 LLM Provider
4. **错误日志** — 终端输出或 `logs/sessions/` 目录中的会话日志

> **调试技巧**
>
> 用浏览器打开 `tools/log_analyzer.html`，将 `.jsonl` 会话日志拖入页面，即可可视化查看 LLM 调用、Agent 执行流程和错误信息，快速定位问题。

---

## 请求新功能

有好想法？通过 [功能请求](https://github.com/ypcypc/WhatIf/issues/new?template=feature_request.md) 提交 Issue。

请描述清楚：

- 这个功能解决什么问题 / 改善什么体验
- 你期望的功能表现
- 你考虑过的替代方案（如有）

---

## 提交代码

### 流程概览

```
Fork → Clone → Branch → Code → Test → Commit → Push → PR
```

1. **Fork** 本仓库并克隆到本地
2. 从 `main` 创建功能分支：`git checkout -b feature/your-feature`
3. 编写代码（遵循下方[代码风格](#代码风格)）
4. 测试改动（见下方[测试](#测试你的改动)）
5. Commit — 写清改动说明，一句话概括 what + why
6. Push 到你的 Fork
7. 发起 Pull Request

### 测试你的改动

**后端** — 确保所有核心模块可以正常导入：

```bash
cd backend
python -c "import config; import core; import runtime; import api; print('All modules OK')"
```

**前端** — 确保可以正常构建：

```bash
cd frontend
pnpm build
```

**全栈** — 确保 `start.py` 可以正常启动后端和前端。

### PR 建议

- **一个 PR 只做一件事**，保持改动范围小而集中
- 标题使用 [Conventional Commits](https://www.conventionalcommits.org/) 风格：
  - `fix: 修复 L0 压缩在空历史时的崩溃`
  - `feat: 添加 Ollama Provider 支持`
  - `docs: 更新 README 安装步骤`
- 描述为什么要做此改动

---

## 开发环境搭建

### 环境要求

| 依赖        | 版本   | 说明                         |
| ----------- | ------ | ---------------------------- |
| Python      | 3.10+  | 后端运行环境                 |
| Node.js     | 20+    | 前端开发（仅网页端需要）     |
| pnpm        | 最新版 | 前端包管理器                 |
| LLM API Key | —     | 至少需要一个 Provider 的 Key |

### 搭建

```bash
# 1. Clone
git clone https://github.com/ypcypc/WhatIf.git
cd WhatIf

# 2. Python 环境
python -m venv .venv
# Windows:  .\.venv\Scripts\Activate.ps1
# macOS/Linux:  source .venv/bin/activate
cd backend && pip install -r requirements.txt && python -m spacy download zh_core_web_sm

# 3. API Key
cp .env.example .env
# 编辑 .env，填入至少一个 Provider 的 Key

# 4. 前端（可选，仅网页端开发需要）
cd ../frontend && pnpm install
```

### 项目结构

```
WhatIf/
├── backend/
│   ├── config.py                     #   全局配置
│   ├── core/
│   ├── preprocessing/                #   小说数据提取管线
│   ├── runtime/                      #   游戏引擎
│   │   ├── game.py                   #     GameEngine 主循环
|   |   ├── extract.py                #     Preprocessing 入口
│   │   └── agents/                   #     6 类 Agent
│   │       ├── base.py               #       BaseLLMCaller, BaseAgent, AgentExecutor
│   │       ├── narrative_generation/  #       叙事生成主管线，调度器 + 写作
│   │       ├── context_enrichment/    #       历史召回 + 实体查询
│   │       ├── deviation_guidance/    #       偏离检测 + 引导
│   │       ├── delta_lifecycle/       #       替代时间线管理
│   │       ├── scene_adaptation/      #       场景过渡
│   │       └── memory_compression/    #       记忆压缩
│   └── api/                          #   FastAPI + SSE 接口
├── frontend/                         # React 19 + TypeScript + Tailwind
├── tools/                            # 独立工具（日志分析器）
└── start.py                          # 全栈启动脚本
```

### 文件说明

| 文件                               | 更改场景                                               |
| ---------------------------------- | ---------------------------------------------------------- |
| `backend/config.py`              | 添加 Provider、调整模型映射、修改 Agent 配置               |
| `backend/core/llm.py`            | 修改 LLM 调用逻辑、添加 Provider 鉴权                      |
| `backend/core/models.py`         | 修改数据模型（事件、角色、物品等）                         |
| `backend/runtime/game.py`        | 修改游戏主循环、状态机、存档逻辑                           |
| `backend/runtime/agents/base.py` | 修改 Agent 框架（BaseLLMCaller、BaseAgent、AgentExecutor） |
| `backend/api/routes/game.py`     | 修改 API 端点、SSE 流式逻辑                                |

## 扩展指南

### 添加新的 LLM Provider

见 README.md

### 添加新的 Agent

1. 在 backend/runtime/agents/<new_agent>/ 新建 Agent，实现 BaseAgent.execute()
2. 若需 LLM，建 Caller 继承 BaseLLMCaller
3. 在 backend/llm_config.yaml 增加对应配置
4. 在 backend/config.py 的 _REQUIRED_KEYS 加上新 key
5. 在 backend/runtime/game.py 注册到 AgentExecutor
6. 在 backend/runtime/agents/__init__.py 导出，便于统一引用，此为可选步骤

## 许可

参与贡献即表示你同意你的贡献将以 [MIT 许可证](../LICENSE) 发布。
