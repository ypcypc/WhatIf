# 参与贡献

感谢你对 WhatIf 的关注。欢迎提交 Bug、功能建议、文档修订和代码改动。

AI 辅助的 PR 也欢迎，但请确保你理解并验证自己提交的内容。

---

> **目录**
>
> [报告 Bug](#报告-bug) · [请求新功能](#请求新功能) · [提交代码](#提交代码) · [开发环境搭建](#开发环境搭建) · [代码风格](#代码风格) · [扩展指南](#扩展指南)

---

## 报告 Bug

请通过 [Bug 报告](https://github.com/ypcypc/WhatIf/issues/new?template=bug_report.md) 提交 Issue。

**一份好的 Bug 报告应包含：**

1. **复现步骤**：按步骤描述，让其他人可以稳定复现
2. **期望 vs 实际行为**：你期望发生什么，实际发生了什么
3. **环境信息**：操作系统、Python/Node.js 版本、使用的模型配置
4. **错误日志**：终端输出，或 `logs/sessions/` 下的会话日志

> **调试建议**
>
> 用浏览器打开 `tools/log_analyzer.html`，将 `.jsonl` 会话日志拖入页面，可查看 LLM 调用、Agent 执行流程和错误信息。

---

## 请求新功能

有新想法时，请通过 [功能请求](https://github.com/ypcypc/WhatIf/issues/new?template=feature_request.md) 提交 Issue。

请尽量说明：

- 这个功能解决什么问题
- 你期望的行为是什么
- 你考虑过哪些替代方案

---

## 提交代码

### 流程概览

```text
Fork -> Clone -> Branch -> Code -> Test -> Commit -> Push -> PR
```

1. Fork 本仓库并克隆到本地
2. 从 `main` 创建功能分支：`git checkout -b feature/your-feature`
3. 编写代码
4. 测试改动
5. Commit：一句话说明改了什么、为什么改
6. Push 到你的 Fork
7. 发起 Pull Request

### 测试你的改动

**后端**

```bash
cd backend
python -c "import config; import core; import runtime; import api; print('All modules OK')"
```

**前端**

```bash
cd frontend
pnpm build
```

**全栈**

确认 `start.py` 可以正常启动前后端。

### PR 建议

- 一个 PR 只做一件事
- 改动尽量小，避免顺手重构
- 标题建议使用 [Conventional Commits](https://www.conventionalcommits.org/) 风格
  - `fix: 修复 L0 压缩在空历史时的崩溃`
  - `feat: 添加新的 Scene Agent`
  - `docs: 更新 CONTRIBUTING 扩展指南`
- PR 描述中写清楚 why，不只写 what

---

## 开发环境搭建

### 环境要求

| 依赖 | 版本 | 说明 |
| --- | --- | --- |
| Python | 3.10+ | 后端运行环境 |
| Node.js | 20.19+ 或 22.12+ | 前端开发与构建 |
| pnpm | 9+ | 前端包管理器 |
| LLM API Key | 至少一个 | 按 `backend/llm_config.yaml` 中实际使用的模型提供 |

### 快速搭建

```bash
# 1. Clone
git clone https://github.com/ypcypc/WhatIf.git
cd WhatIf

# 2. Python 环境
python -m venv .venv
# Windows: .\.venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate

# 3. 后端依赖
cd backend
pip install -r requirements.txt
python -m spacy download zh_core_web_sm
cd ..

# 4. API Key
cp backend/.env.example backend/.env
# 编辑 backend/.env
# 只需要填写 backend/llm_config.yaml 中实际使用的 Provider 对应的 Key

# 5. 前端（可选，仅网页端开发需要）
cd frontend
pnpm install
```

### 项目结构

```text
WhatIf/
├── backend/
│   ├── config.py                     # 配置加载与校验
│   ├── llm_config.yaml               # 所有提取器和 Agent 的 LLM 配置
│   ├── core/                         # LLM 客户端、共享模型、核心 Prompt
│   ├── preprocessing/                # 提取管线
│   ├── runtime/                      # 游戏引擎
│   │   ├── game.py                   # GameEngine 主循环与 Agent 注册
│   │   └── agents/                   # 6 个运行期 Agent
│   └── api/                          # FastAPI + SSE 接口
├── frontend/                         # React 19 + TypeScript + Vite
├── tools/                            # 日志分析等独立工具
└── start.py                          # 本地全栈启动脚本
```

### 关键文件

| 文件 | 改动场景 |
| --- | --- |
| `backend/llm_config.yaml` | 切换模型、切换 Provider、调整温度/思考预算/额外参数 |
| `backend/config.py` | 修改 LLM 配置校验、必需配置键、API Key 校验逻辑 |
| `backend/core/llm.py` | 修改 LLM 请求封装、参数转译、结构化输出逻辑 |
| `backend/core/models.py` | 修改共享数据模型 |
| `backend/runtime/game.py` | 修改游戏主循环、状态流转、Agent 注册 |
| `backend/runtime/agents/base.py` | 修改 Agent 框架基类 |
| `backend/api/routes/game.py` | 修改游戏 API 与 SSE 流式逻辑 |

---

## 代码风格

- 保持改动最小，不顺手重构无关代码
- 新逻辑优先复用现有抽象，而不是再造一层
- 文档口径必须和代码一致；改了配置方式，就同步改 README / CONTRIBUTING
- Prompt、配置、接口字段名尽量稳定，避免无意义改名

---

## 扩展指南

### 添加新的 LLM Provider

当前项目的模型配置不再写死在 Python 字典里，而是统一放在 `backend/llm_config.yaml`。

通常只需要做这几步：

1. 在 `backend/llm_config.yaml` 中修改对应提取器或 Agent 的配置
   - 必填：`model`
   - 可选：`temperature`、`thinking_budget`、`extra_params`、`api_base`、`api_key_env`
2. 在 `backend/.env.example` 中添加新 Provider 的 Key 占位符和申请链接
3. 如果该 Provider 的 Key 名能从模型前缀自动推断，就不需要改代码
4. 如果不能自动推断，就在 YAML 中显式填写 `api_key_env`
5. 重新导入 `backend/config.py` 或直接启动项目，确认配置校验通过

**什么时候需要改 Python 代码**

- 只有当新 Provider 需要新的默认参数转译逻辑时，才需要改 `backend/core/llm.py`
- 只有当你希望模型前缀自动映射到某个环境变量名时，才需要改 `backend/config.py` 中的 `_PROVIDER_KEY_MAP`

### 添加新的 Agent

当前实现下，新增 Agent 至少要完成这几步：

1. 在 `backend/runtime/agents/` 下创建新目录，例如 `my_agent/`
2. 实现 `agent.py`，继承 `BaseAgent`，实现 `execute()`
3. 如需 LLM 调用，创建 Caller 类继承 `BaseLLMCaller`，并把 Prompt 放到同目录的 `prompts/` 下
4. 在 `backend/llm_config.yaml` 中为这个 Agent 添加配置项
5. 在 `backend/config.py` 的 `_REQUIRED_KEYS` 中加入同名 key
6. 在 `backend/runtime/game.py` 中把新 Agent 注册到 `AgentExecutor`
7. 如有统一导出需求，再更新 `backend/runtime/agents/__init__.py`

> `backend/runtime/agents/__init__.py` 的导出不是运行必需条件；真正决定 Agent 是否参与执行的是 `backend/runtime/game.py` 中的注册。

---

## 许可

参与贡献即表示你同意你的贡献将以 [MIT 许可证](../LICENSE) 发布。
