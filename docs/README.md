# WhatIf AI Galgame 项目文档

欢迎来到 WhatIf AI Galgame 项目文档！这是一个基于 AI 技术的视觉小说游戏系统，结合了现代前端技术和强大的后端服务。

## 项目概述

WhatIf 是一个创新的 AI 驱动的视觉小说（Galgame）系统，旨在为用户提供沉浸式的互动阅读体验。系统采用微服务架构，将不同功能模块分离，确保高可维护性和可扩展性。

## 核心特性

- 🎮 **沉浸式 Galgame 界面** - 完整的视觉小说游戏体验
- 🔗 **智能锚点系统** - 基于锚点的文本上下文构造
- 🤖 **AI 集成** - 支持 OpenAI GPT 等大语言模型
- 📚 **顺序阅读** - 流畅的章节和文本块导航
- 💾 **状态管理** - 游戏进度保存和加载
- 🎨 **现代化前端** - React + TypeScript + Vite 技术栈

## 系统架构

```
WhatIf AI Galgame
├── 前端 (React + TypeScript)
│   ├── 主界面 (Galgame UI)
│   ├── 游戏阅读器
│   ├── 锚点上下文演示
│   └── API 连通性测试
├── 后端服务 (FastAPI + Python)
│   ├── anchor_service (锚点服务)
│   ├── llm_service (LLM 服务)
│   ├── dict_service (字典服务)
│   └── save_service (保存服务)
└── 数据层
    ├── 文章数据 (JSON)
    ├── 角色数据
    └── 故事线数据
```

## 快速开始

### 环境要求

- Python 3.13.4
- Node.js 20
- Poetry (Python 包管理)
- pnpm/npm (Node.js 包管理)

### 启动后端服务

```bash
# 使用启动脚本（推荐）
./start_backend.sh

# 或手动启动
cd backend_services
poetry install
poetry run uvicorn app.main:app --reload --port 8000
```

### 启动前端服务

```bash
# 安装依赖
pnpm install

# 启动开发服务器
pnpm dev
```

### 访问应用

- **前端界面**: http://localhost:5173
- **后端 API**: http://localhost:8000
- **API 文档**: http://localhost:8000/docs

## 文档导航

- [Anchor Service 文档](./anchor-service.md) - 锚点服务详细说明
- [LLM Service 文档](./llm-service.md) - 大语言模型服务文档
- [前端开发文档](./frontend.md) - 前端架构和组件说明
- [API 参考](./api-reference.md) - 完整的 API 接口文档
- [部署指南](./deployment.md) - 生产环境部署说明

## 技术栈

### 前端技术
- **React 18** - 用户界面框架
- **TypeScript** - 类型安全的 JavaScript
- **Vite** - 快速构建工具
- **Tailwind CSS** - 实用优先的 CSS 框架
- **Lucide React** - 现代图标库

### 后端技术
- **FastAPI** - 现代 Python Web 框架
- **Pydantic** - 数据验证和序列化
- **Uvicorn** - ASGI 服务器
- **Poetry** - Python 依赖管理

### 开发工具
- **ESLint** - JavaScript/TypeScript 代码检查
- **Prettier** - 代码格式化
- **Git** - 版本控制

## 贡献指南

我们欢迎社区贡献！请阅读以下指南：

1. Fork 项目仓库
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

## 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](../LICENSE) 文件。

## 联系我们

如有问题或建议，请通过以下方式联系：

- 创建 GitHub Issue
- 发送邮件至项目维护者
- 加入我们的开发者社区

---

*最后更新: 2025年7月16日*
