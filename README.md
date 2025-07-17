# WhatIf AI Galgame

一个基于AI技术的交互式视觉小说游戏系统。

## 项目概述

WhatIf 是一个创新的 AI 驱动的视觉小说（Galgame）系统，旨在为用户提供沉浸式的互动阅读体验。系统采用微服务架构，将不同功能模块分离，确保高可维护性和可扩展性。

## 快速开始

### 启动后端服务

```bash
# 使用启动脚本（推荐）
./start_backend.sh

# 或手动启动
poetry install
poetry run python start_backend.py
```

### 启动前端服务

```bash
# 安装依赖
pnpm install

# 启动开发服务器
pnpm dev
```

## 技术栈

- **后端**: FastAPI + Python 3.13
- **前端**: React + TypeScript + Vite
- **AI**: OpenAI GPT-4 mini
- **数据**: JSON + 事件流

## 访问地址

- **前端界面**: http://localhost:5173
- **后端API**: http://localhost:8000
- **API文档**: http://localhost:8000/docs

## 文档

详细文档请参考 [docs](./docs/) 目录。