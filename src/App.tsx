import { useState } from 'react'
import { 
  Save, 
  Upload, 
  Settings, 
  Volume2, 
  Maximize2, 
  List, 
  FastForward, 
  SkipForward, 
  BookOpen, 
  X, 
  Music,
  Play,
  Pause,
  Camera,
  Users,
  TestTube
} from 'lucide-react'
import './App.css'
import AnchorServiceTest from './components/AnchorServiceTest'
import GameReader from './components/GameReader'
import AnchorContextDemo from './components/AnchorContextDemo'
import InteractiveGameReader from './components/InteractiveGameReader'

function App() {
  const [currentScene, setCurrentScene] = useState('main')
  const [showOptions, setShowOptions] = useState(false)
  const [dialogueText, setDialogueText] = useState('欢迎来到 AI Galgame 演示系统！点击下方的"选项"按钮来体验不同的功能模块。')
  const [characterName, setCharacterName] = useState('系统')
  const [showBacklog, setShowBacklog] = useState(false)
  const [isPlaying, setIsPlaying] = useState(true)
  const [volume, setVolume] = useState(true)
  const [showAnchorTest, setShowAnchorTest] = useState(false)
  const [showGameReader, setShowGameReader] = useState(false)
  const [showContextDemo, setShowContextDemo] = useState(false)
  const [showInteractiveGame, setShowInteractiveGame] = useState(false)

  // Show GameReader if enabled
  if (showGameReader) {
    return <GameReader onBack={() => setShowGameReader(false)} />;
  }

  // Show AnchorContextDemo if enabled
  if (showContextDemo) {
    return <AnchorContextDemo onBack={() => setShowContextDemo(false)} />;
  }

  // Show Interactive Game if enabled
  if (showInteractiveGame) {
    return <InteractiveGameReader onBack={() => setShowInteractiveGame(false)} />;
  }

  // Show anchor service test if enabled
  if (showAnchorTest) {
    return (
      <div className="galgame-container">
        {/* 顶部状态栏 */}
        <div className="top-status-bar">
          <div className="status-left">
            <button 
              className="status-btn" 
              title="返回游戏"
              onClick={() => setShowAnchorTest(false)}
            >
              <X size={16} />
              <span>返回</span>
            </button>
          </div>
          <div className="status-right">
            <span className="text-sm text-gray-600">Anchor Service 连通性测试</span>
          </div>
        </div>
        
        {/* 测试组件区域 */}
        <div className="test-container p-4 overflow-y-auto" style={{ height: 'calc(100vh - 60px)' }}>
          <AnchorServiceTest />
        </div>
      </div>
    );
  }

  return (
    <div className="galgame-container">
      {/* 顶部状态栏 */}
      <div className="top-status-bar">
        <div className="status-left">
          <button className="status-btn" title="存档">
            <Save size={16} />
            <span>存档</span>
          </button>
          <button className="status-btn" title="读档">
            <Upload size={16} />
            <span>读档</span>
          </button>
          <button className="status-btn" title="设置">
            <Settings size={16} />
            <span>设置</span>
          </button>
          <button 
            className="status-btn" 
            title="Anchor Service 测试"
            onClick={() => setShowAnchorTest(!showAnchorTest)}
          >
            <TestTube size={16} />
            <span>测试</span>
          </button>
        </div>
        <div className="status-right">
          <button 
            className="status-btn icon-only" 
            title="音量"
            onClick={() => setVolume(!volume)}
          >
            <Volume2 size={18} />
          </button>
          <button className="status-btn icon-only" title="全屏">
            <Maximize2 size={18} />
          </button>
        </div>
      </div>

      {/* 背景全屏展示区 */}
      <div className="background-layer">
        <div className="background-image">
          {/* 背景图片将在这里 */}
          <div className="background-placeholder">
            <Camera size={48} />
            <span>背景图片区域</span>
          </div>
        </div>
        <div className="background-overlay"></div>
      </div>

      {/* CG画面/角色立绘层 */}
      <div className="content-layer">
        <div className="cg-area">
          <div className="cg-placeholder">
            <Camera size={32} />
            <span>CG 大图区域</span>
          </div>
        </div>
        <div className="sprite-area">
          <div className="character-sprite">
            <div className="sprite-placeholder">
              <Users size={32} />
              <span>角色立绘层</span>
            </div>
          </div>
        </div>
      </div>

      {/* 对话框区域 */}
      <div className="dialogue-panel">
        <div className="dialogue-container">
          <div className="name-box">
            <span className="character-name">{characterName}</span>
          </div>
          <div className="dialogue-box">
            <p className="dialogue-text">{dialogueText}</p>
          </div>
        </div>
      </div>

      {/* 操作按钮区 */}
      <div className="control-panel">
        <div className="control-left">
          {showOptions && (
            <div className="choice-buttons">
              <button 
                className="choice-btn"
                onClick={() => setShowGameReader(true)}
              >
                开始阅读故事
              </button>
              <button 
                className="choice-btn"
                onClick={() => setShowInteractiveGame(true)}
              >
                AI交互式故事
              </button>
              <button 
                className="choice-btn"
                onClick={() => setShowContextDemo(true)}
              >
                锚点上下文演示
              </button>
              <button 
                className="choice-btn"
                onClick={() => setShowAnchorTest(true)}
              >
                API连通性测试
              </button>
            </div>
          )}
        </div>
        <div className="control-right">
          <button 
            className="control-btn" 
            onClick={() => setShowOptions(!showOptions)}
            title="选项"
          >
            <List size={16} />
            <span>选项</span>
          </button>
          <button 
            className="control-btn"
            onClick={() => setIsPlaying(!isPlaying)}
            title={isPlaying ? "暂停" : "播放"}
          >
            {isPlaying ? <Pause size={16} /> : <Play size={16} />}
            <span>{isPlaying ? "暂停" : "播放"}</span>
          </button>
          <button className="control-btn" title="快进">
            <FastForward size={16} />
            <span>快进</span>
          </button>
          <button className="control-btn" title="跳过">
            <SkipForward size={16} />
            <span>跳过</span>
          </button>
          <button 
            className="control-btn" 
            onClick={() => setShowBacklog(!showBacklog)}
            title="日志"
          >
            <BookOpen size={16} />
            <span>日志</span>
          </button>
        </div>
      </div>

      {/* 历史记录面板 */}
      {showBacklog && (
        <div className="backlog-panel">
          <div className="backlog-header">
            <div className="backlog-title">
              <BookOpen size={20} />
              <h3>对话历史</h3>
            </div>
            <button className="close-btn" onClick={() => setShowBacklog(false)}>
              <X size={20} />
            </button>
          </div>
          <div className="backlog-content">
            <div className="backlog-item">
              <div className="backlog-name">旁白</div>
              <div className="backlog-text">欢迎来到这个美丽的世界...</div>
            </div>
            <div className="backlog-item">
              <div className="backlog-name">角色A</div>
              <div className="backlog-text">这里是一些历史对话记录...</div>
            </div>
            <div className="backlog-item">
              <div className="backlog-name">角色B</div>
              <div className="backlog-text">更多的对话内容将显示在这里...</div>
            </div>
            <div className="backlog-item">
              <div className="backlog-name">角色C</div>
              <div className="backlog-text">您可以在这里回顾之前的所有对话内容...</div>
            </div>
            <div className="backlog-item">
              <div className="backlog-name">旁白</div>
              <div className="backlog-text">这是一个完整的对话历史记录系统...</div>
            </div>
          </div>
        </div>
      )}

      {/* 音效提示区 */}
      <div className="audio-indicator">
        <div className="audio-placeholder">
          <Music size={24} />
        </div>
      </div>
    </div>
  )
}

export default App
