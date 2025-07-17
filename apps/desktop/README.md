# Desktop App (Electron)

WhatIf AI Galgame 的桌面应用程序，基于 Electron + React 19 构建。

## 项目结构

```
apps/desktop/
├── electron/
│   ├── main.ts          # Electron 主进程
│   ├── preload.ts       # 预加载脚本
│   └── electron-env.d.ts
├── src/
│   ├── App.tsx          # React 应用入口
│   ├── main.tsx         # React 主渲染文件
│   ├── assets/          # 静态资源
│   └── ...
├── public/              # 公共资源
├── package.json         # 依赖配置
├── vite.config.ts       # Vite 配置
├── electron-builder.json5  # Electron Builder 配置
└── README.md            # 本文档
```

## 技术栈

- **Electron** - 跨平台桌面应用框架
- **React 19** - 用户界面库
- **TypeScript** - 类型安全的 JavaScript
- **Vite** - 快速构建工具
- **Electron Builder** - 应用打包工具

## 开发环境

### 先决条件

- Node.js 18+
- pnpm 8+
- Python 3.10+ (用于后端服务)

### 安装依赖

```bash
# 从项目根目录
cd apps/desktop

# 安装依赖
pnpm install
```

### 开发模式

```bash
# 启动开发服务器
pnpm run dev

# 启动 Electron (在另一个终端)
pnpm run electron:dev
```

### 构建应用

```bash
# 构建 Web 应用
pnpm run build

# 构建 Electron 应用
pnpm run electron:build

# 打包应用程序
pnpm run dist
```

## 脚本命令

| 命令 | 描述 |
|------|------|
| `pnpm run dev` | 启动开发服务器 (Vite) |
| `pnpm run build` | 构建生产版本 |
| `pnpm run preview` | 预览生产构建 |
| `pnpm run electron:dev` | 开发模式启动 Electron |
| `pnpm run electron:build` | 构建 Electron 应用 |
| `pnpm run dist` | 打包可分发应用 |
| `pnpm run dist:win` | 打包 Windows 版本 |
| `pnpm run dist:mac` | 打包 macOS 版本 |
| `pnpm run dist:linux` | 打包 Linux 版本 |

## 应用架构

### 主进程 (main.ts)

负责管理应用程序的生命周期、创建窗口和处理系统级事件。

主要功能：
- 窗口管理
- 菜单设置
- 文件系统访问
- 与渲染进程通信
- Python 后端服务集成

### 预加载脚本 (preload.ts)

在渲染进程中运行，但具有 Node.js API 访问权限，用于安全地暴露 API 给渲染进程。

主要功能：
- IPC 通信桥接
- 安全的文件操作
- 系统信息获取

### 渲染进程 (React App)

运行 React 应用程序，负责用户界面和用户交互。

主要功能：
- 游戏界面渲染
- 用户输入处理
- 状态管理 (XState)
- 动画效果 (Framer Motion)

## 与后端集成

### Python 服务集成

桌面应用通过以下方式与 Python 后端服务通信：

1. **子进程启动**
   ```typescript
   // 在主进程中启动 Python 服务
   const pythonProcess = spawn('python', ['-m', 'uvicorn', 'llm_services.app.api:app']);
   ```

2. **HTTP 通信**
   ```typescript
   // 渲染进程通过 HTTP 调用后端 API
   const response = await fetch('http://localhost:8000/chat/invoke', {
     method: 'POST',
     body: JSON.stringify(requestData)
   });
   ```

3. **IPC 消息传递**
   ```typescript
   // 主进程 -> 渲染进程
   mainWindow.webContents.send('python-service-status', status);
   
   // 渲染进程 -> 主进程
   ipcRenderer.invoke('start-python-service');
   ```

## 配置

### Electron Builder 配置

`electron-builder.json5` 文件配置应用打包选项：

```json5
{
  "appId": "com.whatif.galgame",
  "productName": "WhatIf AI Galgame",
  "directories": {
    "buildResources": "build"
  },
  "files": [
    "dist-electron",
    "dist"
  ],
  "mac": {
    "icon": "build/icon.icns"
  },
  "win": {
    "icon": "build/icon.ico"
  },
  "linux": {
    "icon": "build/icon.png"
  }
}
```

### Vite 配置

`vite.config.ts` 配置开发和构建选项：

```typescript
export default defineConfig({
  plugins: [react()],
  base: './',
  build: {
    outDir: 'dist',
    emptyOutDir: true
  },
  server: {
    port: 3000
  }
});
```

## 开发指南

### 添加新功能

1. **渲染进程功能**
   - 在 `src/` 目录添加 React 组件
   - 使用 XState 管理复杂状态
   - 通过 IPC 与主进程通信

2. **主进程功能**
   - 在 `electron/main.ts` 添加功能
   - 使用 IPC 处理渲染进程请求
   - 集成系统级 API

3. **预加载脚本**
   - 在 `electron/preload.ts` 暴露安全 API
   - 避免直接暴露 Node.js API

### 调试

#### 开发者工具
```typescript
// 在主进程中打开开发者工具
mainWindow.webContents.openDevTools();
```

#### 主进程调试
```bash
# 使用 --inspect 启动
pnpm run electron:dev --inspect
```

#### 日志记录
```typescript
// 渲染进程
console.log('Renderer log');

// 主进程
console.log('Main process log');
```

## 安全考虑

### 禁用 Node.js 集成
```typescript
const mainWindow = new BrowserWindow({
  webPreferences: {
    nodeIntegration: false,
    contextIsolation: true,
    preload: path.join(__dirname, 'preload.js')
  }
});
```

### 安全的 IPC 通信
```typescript
// 预加载脚本中的安全 API 暴露
contextBridge.exposeInMainWorld('electronAPI', {
  openFile: () => ipcRenderer.invoke('dialog:openFile')
});
```

## 性能优化

### 启动优化
- 延迟加载非关键模块
- 使用 `app.whenReady()` 确保初始化完成
- 预加载关键资源

### 渲染优化
- 使用 React.memo 避免不必要的重渲染
- 虚拟化长列表
- 图片懒加载

### 内存管理
- 及时清理事件监听器
- 避免内存泄漏
- 使用 WeakMap/WeakSet

## 构建和分发

### 开发构建
```bash
pnpm run electron:build
```

### 生产构建
```bash
pnpm run dist
```

### 平台特定构建
```bash
# Windows
pnpm run dist:win

# macOS
pnpm run dist:mac

# Linux
pnpm run dist:linux
```

## 故障排除

### 常见问题

1. **Electron 启动失败**
   - 检查 Node.js 版本兼容性
   - 确认依赖安装完整

2. **Python 服务无法启动**
   - 检查 Python 环境配置
   - 确认后端依赖安装

3. **构建失败**
   - 清理缓存: `pnpm run clean`
   - 重新安装依赖: `rm -rf node_modules && pnpm install`

4. **IPC 通信问题**
   - 检查预加载脚本配置
   - 确认上下文隔离设置正确

## 许可证

MIT License
