# 前端开发文档

WhatIf AI Galgame 前端是一个基于 React + TypeScript 的现代化单页应用，提供沉浸式的视觉小说游戏体验。

## 概述

前端采用组件化架构，实现了完整的 Galgame 界面和交互功能，包括：
- 沉浸式游戏界面
- 顺序阅读系统
- 锚点上下文演示
- API 连通性测试
- 响应式设计

## 技术栈

### 核心框架
- **React 18** - 用户界面库
- **TypeScript** - 类型安全的 JavaScript
- **Vite** - 快速构建工具和开发服务器

### 样式和 UI
- **Tailwind CSS** - 实用优先的 CSS 框架
- **CSS Modules** - 组件级样式隔离
- **Lucide React** - 现代图标库

### 开发工具
- **ESLint** - 代码质量检查
- **PostCSS** - CSS 后处理器
- **pnpm** - 高效的包管理器

## 项目结构

```
src/
├── components/           # React 组件
│   ├── GameReader.tsx   # 游戏阅读器组件
│   ├── GameReader.css   # 游戏阅读器样式
│   ├── AnchorContextDemo.tsx    # 锚点上下文演示
│   └── AnchorServiceTest.tsx    # API 测试组件
├── services/            # API 服务层
│   └── anchorService.ts # 锚点服务接口
├── assets/             # 静态资源
│   └── react.svg       # 图标资源
├── App.tsx             # 主应用组件
├── App.css             # 全局样式
├── main.tsx            # 应用入口
└── index.css           # 基础样式
```

## 核心组件

### 1. App.tsx - 主应用组件

主应用组件实现了 Galgame 风格的界面布局：

```typescript
function App() {
  const [showGameReader, setShowGameReader] = useState(false);
  const [showContextDemo, setShowContextDemo] = useState(false);
  const [showAnchorTest, setShowAnchorTest] = useState(false);
  
  // 条件渲染不同的功能模块
  if (showGameReader) {
    return <GameReader onBack={() => setShowGameReader(false)} />;
  }
  
  // 主界面布局
  return (
    <div className="galgame-container">
      {/* 顶部状态栏 */}
      <div className="top-status-bar">...</div>
      
      {/* 背景和内容层 */}
      <div className="background-layer">...</div>
      <div className="content-layer">...</div>
      
      {/* 对话框区域 */}
      <div className="dialogue-panel">...</div>
      
      {/* 控制按钮 */}
      <div className="control-panel">...</div>
    </div>
  );
}
```

#### 主要功能
- **状态管理**: 使用 React Hooks 管理组件状态
- **条件渲染**: 根据用户选择显示不同功能模块
- **事件处理**: 处理用户交互和导航
- **响应式布局**: 适配不同屏幕尺寸

### 2. GameReader.tsx - 游戏阅读器

游戏阅读器是核心的阅读体验组件：

```typescript
interface GameReaderProps {
  onBack: () => void;
}

const GameReader: React.FC<GameReaderProps> = ({ onBack }) => {
  const [currentChunk, setCurrentChunk] = useState<ChunkResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // 获取下一个文本块
  const getNext = useCallback(async () => {
    if (!currentChunk) return;
    
    try {
      const nextChunk = await getNextChunk(currentChunk.chunk_id);
      setCurrentChunk(nextChunk);
    } catch (err) {
      setError(err.message);
    }
  }, [currentChunk]);
  
  // 键盘事件处理
  useEffect(() => {
    const handleKeyPress = (event: KeyboardEvent) => {
      if (event.key === 'Enter' || event.key === ' ') {
        getNext();
      }
    };
    
    document.addEventListener('keydown', handleKeyPress);
    return () => document.removeEventListener('keydown', handleKeyPress);
  }, [getNext]);
  
  return (
    <div className="galgame-container" onClick={getNext}>
      {/* Galgame 界面布局 */}
    </div>
  );
};
```

#### 核心特性
- **顺序阅读**: 支持点击或键盘继续阅读
- **状态管理**: 管理当前文本块和加载状态
- **错误处理**: 优雅处理 API 错误
- **键盘支持**: Enter/Space 键继续阅读
- **视觉反馈**: 加载状态和进度显示

### 3. AnchorContextDemo.tsx - 锚点上下文演示

演示锚点上下文构造功能的组件：

```typescript
const AnchorContextDemo: React.FC<{ onBack: () => void }> = ({ onBack }) => {
  const [contextResult, setContextResult] = useState<ContextResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  
  const handleBuildContext = async () => {
    setIsLoading(true);
    try {
      const result = await buildAnchorContext({
        current_anchor: { node_id: "a1_5", chunk_id: "ch1_23", chapter_id: 1 },
        previous_anchor: { node_id: "a1_4", chunk_id: "ch1_15", chapter_id: 1 },
        include_tail: false,
        is_last_anchor_in_chapter: false
      });
      setContextResult(result);
    } catch (error) {
      console.error('构造上下文失败:', error);
    } finally {
      setIsLoading(false);
    }
  };
  
  return (
    <div className="demo-container">
      {/* 演示界面 */}
    </div>
  );
};
```

#### 功能特点
- **交互式演示**: 用户可以调整参数测试不同场景
- **实时反馈**: 显示构造结果和统计信息
- **参数配置**: 支持修改锚点和选项参数
- **结果展示**: 格式化显示上下文内容

### 4. AnchorServiceTest.tsx - API 测试组件

用于测试后端 API 连通性的组件：

```typescript
const AnchorServiceTest: React.FC = () => {
  const [testResults, setTestResults] = useState<TestResult[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  
  const runTests = async () => {
    setIsRunning(true);
    const results: TestResult[] = [];
    
    // 测试各个 API 端点
    const tests = [
      { name: '获取第一个文本块', test: () => getFirstChunk() },
      { name: '构造锚点上下文', test: () => buildAnchorContext({...}) },
      // 更多测试...
    ];
    
    for (const test of tests) {
      try {
        await test.test();
        results.push({ name: test.name, status: 'success' });
      } catch (error) {
        results.push({ name: test.name, status: 'failed', error: error.message });
      }
    }
    
    setTestResults(results);
    setIsRunning(false);
  };
  
  return (
    <div className="test-container">
      {/* 测试界面 */}
    </div>
  );
};
```

## 服务层

### anchorService.ts - API 服务

提供类型安全的 API 调用接口：

```typescript
// 类型定义
export interface ChunkResponse {
  chunk_id: string;
  text: string;
  chapter_id: number;
  next_chunk_id?: string;
  is_last_in_chapter: boolean;
  is_last_overall: boolean;
}

export interface ContextRequest {
  current_anchor: AnchorInfo;
  previous_anchor: AnchorInfo;
  include_tail?: boolean;
  is_last_anchor_in_chapter?: boolean;
}

export interface ContextResponse {
  context: string;
  chunk_count: number;
  total_length: number;
}

// API 调用函数
export async function getFirstChunk(): Promise<ChunkResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/anchor/chunk/first`);
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }
  return response.json();
}

export async function getNextChunk(currentChunkId: string): Promise<ChunkResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/anchor/chunk/next`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ current_chunk_id: currentChunkId })
  });
  
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }
  return response.json();
}

export async function buildAnchorContext(request: ContextRequest): Promise<ContextResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/anchor/context`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request)
  });
  
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }
  return response.json();
}
```

#### 服务层特性
- **类型安全**: 完整的 TypeScript 类型定义
- **错误处理**: 统一的错误处理机制
- **请求封装**: 简化的 API 调用接口
- **配置管理**: 集中的 API 基础 URL 配置

## 样式系统

### 全局样式 (App.css)

实现 Galgame 风格的界面样式：

```css
.galgame-container {
  position: relative;
  width: 100vw;
  height: 100vh;
  overflow: hidden;
  font-family: 'Microsoft YaHei', 'PingFang SC', sans-serif;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
}

.top-status-bar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 60px;
  background: rgba(0, 0, 0, 0.8);
  backdrop-filter: blur(10px);
  z-index: 1000;
}

.dialogue-panel {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 200px;
  background: linear-gradient(to top, rgba(0, 0, 0, 0.9), rgba(0, 0, 0, 0.7));
  backdrop-filter: blur(10px);
}
```

### 组件样式 (GameReader.css)

专门为游戏阅读器设计的样式：

```css
.background-layer {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 1;
}

.content-layer {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 2;
  pointer-events: none;
}

.dialogue-box {
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 12px;
  padding: 20px 24px;
  backdrop-filter: blur(10px);
}
```

## 开发工作流

### 本地开发

```bash
# 安装依赖
pnpm install

# 启动开发服务器
pnpm dev

# 代码检查
pnpm lint

# 类型检查
pnpm type-check

# 构建生产版本
pnpm build
```

### 开发服务器配置

```typescript
// vite.config.ts
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
});
```

## 状态管理

### React Hooks 模式

使用 React 内置的状态管理：

```typescript
// 组件状态
const [currentScene, setCurrentScene] = useState('main');
const [showOptions, setShowOptions] = useState(false);
const [dialogueText, setDialogueText] = useState('欢迎来到 AI Galgame...');

// 副作用处理
useEffect(() => {
  const initializeReader = async () => {
    try {
      const firstChunk = await getFirstChunk();
      setCurrentChunk(firstChunk);
    } catch (error) {
      setError(error.message);
    }
  };
  
  initializeReader();
}, []);

// 回调函数优化
const handleNext = useCallback(async () => {
  if (!currentChunk || isLoading) return;
  
  setIsLoading(true);
  try {
    const nextChunk = await getNextChunk(currentChunk.chunk_id);
    setCurrentChunk(nextChunk);
  } catch (error) {
    setError(error.message);
  } finally {
    setIsLoading(false);
  }
}, [currentChunk, isLoading]);
```

## 性能优化

### 代码分割

```typescript
// 懒加载组件
const GameReader = lazy(() => import('./components/GameReader'));
const AnchorContextDemo = lazy(() => import('./components/AnchorContextDemo'));

// 使用 Suspense
<Suspense fallback={<div>加载中...</div>}>
  <GameReader onBack={handleBack} />
</Suspense>
```

### 内存优化

```typescript
// 清理事件监听器
useEffect(() => {
  const handleKeyPress = (event: KeyboardEvent) => {
    // 处理键盘事件
  };
  
  document.addEventListener('keydown', handleKeyPress);
  return () => {
    document.removeEventListener('keydown', handleKeyPress);
  };
}, []);

// 避免内存泄漏
useEffect(() => {
  let isMounted = true;
  
  const fetchData = async () => {
    const data = await api.getData();
    if (isMounted) {
      setData(data);
    }
  };
  
  fetchData();
  
  return () => {
    isMounted = false;
  };
}, []);
```

## 响应式设计

### 移动端适配

```css
/* 响应式断点 */
@media (max-width: 768px) {
  .galgame-container {
    font-size: 14px;
  }
  
  .dialogue-panel {
    height: 150px;
    padding: 15px 20px;
  }
  
  .top-status-bar {
    height: 50px;
  }
}

@media (max-width: 480px) {
  .control-panel {
    flex-direction: column;
    gap: 10px;
  }
  
  .choice-buttons {
    flex-direction: column;
  }
}
```

### 触摸支持

```typescript
// 触摸事件处理
const handleTouchStart = (e: TouchEvent) => {
  touchStartX = e.touches[0].clientX;
};

const handleTouchEnd = (e: TouchEvent) => {
  const touchEndX = e.changedTouches[0].clientX;
  const diff = touchStartX - touchEndX;
  
  if (Math.abs(diff) > 50) {
    if (diff > 0) {
      // 向左滑动 - 下一页
      handleNext();
    } else {
      // 向右滑动 - 上一页
      handlePrevious();
    }
  }
};
```

## 测试策略

### 组件测试

```typescript
// GameReader.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import GameReader from './GameReader';

describe('GameReader', () => {
  test('renders game reader interface', () => {
    render(<GameReader onBack={jest.fn()} />);
    expect(screen.getByText('加载中...')).toBeInTheDocument();
  });
  
  test('handles keyboard navigation', () => {
    render(<GameReader onBack={jest.fn()} />);
    fireEvent.keyDown(document, { key: 'Enter' });
    // 验证下一页逻辑
  });
});
```

### API 测试

```typescript
// anchorService.test.ts
import { getFirstChunk, buildAnchorContext } from './anchorService';

describe('anchorService', () => {
  test('getFirstChunk returns valid chunk', async () => {
    const chunk = await getFirstChunk();
    expect(chunk).toHaveProperty('chunk_id');
    expect(chunk).toHaveProperty('text');
    expect(chunk).toHaveProperty('chapter_id');
  });
});
```

## 部署配置

### 构建优化

```typescript
// vite.config.ts
export default defineConfig({
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom'],
          ui: ['lucide-react']
        }
      }
    },
    chunkSizeWarningLimit: 1000
  }
});
```

### 环境配置

```typescript
// 环境变量
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
const NODE_ENV = import.meta.env.MODE;

// 配置对象
export const config = {
  apiBaseUrl: API_BASE_URL,
  isDevelopment: NODE_ENV === 'development',
  isProduction: NODE_ENV === 'production'
};
```

## 故障排除

### 常见问题

1. **API 调用失败**
   - 检查后端服务是否启动
   - 验证 API 基础 URL 配置
   - 查看浏览器网络面板

2. **样式显示异常**
   - 检查 CSS 文件是否正确导入
   - 验证 Tailwind CSS 配置
   - 清除浏览器缓存

3. **组件渲染错误**
   - 查看浏览器控制台错误信息
   - 检查 TypeScript 类型错误
   - 验证组件 props 传递

### 调试工具

- **React Developer Tools** - 组件状态调试
- **浏览器开发者工具** - 网络请求和控制台日志
- **TypeScript 编译器** - 类型检查和错误提示

---

*最后更新: 2025年7月16日*
