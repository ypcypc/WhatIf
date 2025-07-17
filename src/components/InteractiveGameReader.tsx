import React, { useState, useEffect, useCallback, useRef } from 'react';
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
  Users
} from 'lucide-react';
import { 
  startGame, 
  processTurn, 
  generateSessionId,
  type GameStartResponse, 
  type GameTurnResponse, 
  type ScriptUnit, 
  type GameState 
} from '../services/gameService';
import './GameReader.css';

// === Types ===

interface InteractiveGameReaderProps {
  onBack: () => void;
}

interface CurrentDisplay {
  type: 'narration' | 'dialogue' | 'interaction';
  content: string;
  speaker?: string;
  isPlayerChoice?: boolean;
}

// === Main Component ===

const InteractiveGameReader: React.FC<InteractiveGameReaderProps> = ({ onBack }) => {
  // Core state
  const [sessionId] = useState(() => generateSessionId());
  const [gameState, setGameState] = useState<GameState | null>(null);
  const [currentScript, setCurrentScript] = useState<ScriptUnit[]>([]);
  const [currentUnitIndex, setCurrentUnitIndex] = useState(0);
  const [turnNumber, setTurnNumber] = useState(0);
  const [currentAnchor, setCurrentAnchor] = useState<{ chapter_id: number; anchor_index: number } | null>(null);
  
  // UI state - Galgame style
  const [currentDisplay, setCurrentDisplay] = useState<CurrentDisplay | null>(null);
  const [isWaitingForNext, setIsWaitingForNext] = useState(false);
  const [isBusy, setIsBusy] = useState(false);
  const [isInputMode, setIsInputMode] = useState(false);
  const [playerInput, setPlayerInput] = useState('');
  const [defaultReply, setDefaultReply] = useState('');
  const [isUsingDefaultReply, setIsUsingDefaultReply] = useState(false);
  const [showOptions, setShowOptions] = useState(false);
  const [showBacklog, setShowBacklog] = useState(false);
  const [isPlaying, setIsPlaying] = useState(true);
  const [volume, setVolume] = useState(true);
  
  // Status and errors
  const [error, setError] = useState<string | null>(null);
  const [isGameStarted, setIsGameStarted] = useState(false);
  
  // History for backlog
  const [dialogueHistory, setDialogueHistory] = useState<Array<{name: string; text: string; timestamp: number}>>([]);
  
  // Refs
  const inputRef = useRef<HTMLInputElement>(null);

  // === Helper Functions (定义在最前面，避免依赖问题) ===

  const getCharacterFromContent = useCallback((content: string): string => {
    // 尝试从内容中提取角色名称
    if (content.includes('三上悟') || content.includes('我')) {
      return '三上悟';
    }
    if (content.includes('你')) {
      return '主人公';
    }
    // 检查是否有对话引号
    if (content.includes('"') || content.includes("'")) {
      return '对话';
    }
    return '系统';
  }, []);

  const getCharacterName = useCallback((): string => {
    if (!currentDisplay) return '系统';
    
    if (currentDisplay.isPlayerChoice) return '玩家';
    if (currentDisplay.speaker) return currentDisplay.speaker;
    if (currentDisplay.type === 'narration') return '旁白';
    
    // 尝试从内容中识别角色
    return getCharacterFromContent(currentDisplay.content);
  }, [currentDisplay, getCharacterFromContent]);

  const getDialogueText = useCallback((): string => {
    if (!currentDisplay) return '正在加载...';
    return currentDisplay.content;
  }, [currentDisplay]);

  // === Galgame Display Logic ===

  const displayCurrentUnit = useCallback((script: ScriptUnit[], index: number) => {
    console.log(`显示第 ${index + 1} 个单元，总共 ${script.length} 个单元`);
    
    if (index >= script.length) {
      console.log('到达脚本结尾');
      setIsBusy(false);
      setIsWaitingForNext(true);
      return;
    }

    const unit = script[index];
    console.log(`单元类型: ${unit.type}, 内容: ${unit.content.substring(0, 50)}...`);
    
    // Set current display
    setCurrentDisplay({
      type: unit.type,
      content: unit.content,
      speaker: unit.speaker
    });
    
    // Add to dialogue history
    setDialogueHistory(prev => [...prev, {
      name: unit.speaker || (unit.type === 'narration' ? '旁白' : getCharacterFromContent(unit.content)),
      text: unit.content,
      timestamp: Date.now()
    }]);

    // Check if this is an interaction unit
    if (unit.type === 'interaction' && !isInputMode) {
      // Set current display for interaction
      setCurrentDisplay({
        type: 'interaction',
        content: unit.content,
        speaker: unit.speaker
      });
      
      // Set default reply if available
      if (unit.default_reply) {
        setDefaultReply(unit.default_reply);
      }
      
      setIsInputMode(true);
      setIsWaitingForNext(false);
      setIsBusy(false);
      
      // Focus input after short delay
      setTimeout(() => {
        if (inputRef.current) {
          inputRef.current.focus();
        }
      }, 300);
      return;
    }

    // Wait for user to continue
    setIsWaitingForNext(true);
    setIsBusy(false);
  }, [isInputMode, getCharacterFromContent]);

  const showNextUnit = useCallback(() => {
    if (isBusy || isInputMode) return;
    
    const nextIndex = currentUnitIndex + 1;
    setCurrentUnitIndex(nextIndex);
    displayCurrentUnit(currentScript, nextIndex);
  }, [isBusy, isInputMode, currentUnitIndex, currentScript, displayCurrentUnit]);

  // === Core Game Logic ===

  const processPlayerTurn = useCallback(async (playerChoice: string) => {
    if (!currentAnchor || isBusy) return;
    
    setIsBusy(true);
    setError(null);
    setIsInputMode(false);
    setIsWaitingForNext(false);
    
    try {
      console.log('Processing player turn:', playerChoice);
      
      // Add player choice to history
      setDialogueHistory(prev => [...prev, {
        name: '玩家',
        text: playerChoice,
        timestamp: Date.now()
      }]);
      
      // Show player choice in dialogue box briefly
      setCurrentDisplay({
        type: 'dialogue',
        content: playerChoice,
        speaker: '玩家',
        isPlayerChoice: true
      });
      
      // Process turn with backend after short delay
      setTimeout(async () => {
        try {
          const response: GameTurnResponse = await processTurn({
            session_id: sessionId,
            chapter_id: currentAnchor.chapter_id,
            anchor_index: currentAnchor.anchor_index,
            player_choice: playerChoice,
            previous_anchor_index: currentAnchor.anchor_index > 0 ? currentAnchor.anchor_index - 1 : undefined,
            include_tail: false,
            is_last_anchor_in_chapter: false
          });
          
          console.log('Turn processed successfully:', response);
          
          setGameState(response.updated_state);
          setCurrentScript(response.script);
          setTurnNumber(response.turn_number);
          setCurrentAnchor({
            chapter_id: response.anchor_info.chapter_id,
            anchor_index: response.anchor_info.anchor_index
          });
          
          // Start new script display
          setCurrentUnitIndex(0);
          displayCurrentUnit(response.script, 0);
          
        } catch (err) {
          console.error('Failed to process turn:', err);
          setError(err instanceof Error ? err.message : '回合处理失败');
          setIsBusy(false);
        }
      }, 1000);
      
    } catch (err) {
      console.error('Failed to process turn:', err);
      setError(err instanceof Error ? err.message : '回合处理失败');
      setIsBusy(false);
    }
  }, [currentAnchor, isBusy, sessionId, displayCurrentUnit]);

  const startNewGame = useCallback(async () => {
    setIsBusy(true);
    setError(null);
    
    try {
      console.log('Starting new game with session:', sessionId);
      
      const response: GameStartResponse = await startGame({
        session_id: sessionId,
        protagonist: 'c_san_shang_wu',
        chapter_id: 1,
        anchor_index: 0
      });
      
      console.log('Game started successfully:', response);
      
      setGameState(response.game_state);
      setCurrentScript(response.script);
      setTurnNumber(response.turn_number);
      setCurrentAnchor({
        chapter_id: response.current_anchor.chapter_id,
        anchor_index: 0
      });
      setIsGameStarted(true);
      
      // Start Galgame style display
      setCurrentUnitIndex(0);
      displayCurrentUnit(response.script, 0);
      
    } catch (err) {
      console.error('Failed to start game:', err);
      setError(err instanceof Error ? err.message : '游戏启动失败');
    } finally {
      setIsBusy(false);
    }
  }, [sessionId, displayCurrentUnit]);

  // === Event Handlers ===

  const handlePlayerSubmit = useCallback(() => {
    if (!playerInput.trim() || isBusy) return;
    
    const choice = playerInput.trim();
    setPlayerInput('');
    setDefaultReply('');
    setIsUsingDefaultReply(false);
    processPlayerTurn(choice);
  }, [playerInput, isBusy, processPlayerTurn]);

  const handleKeyPress = useCallback((event: KeyboardEvent) => {
    // 只在非输入模式下处理Enter和空格键
    if (!isInputMode && (event.key === 'Enter' || event.key === ' ')) {
      event.preventDefault();
      if (isWaitingForNext && !isBusy) {
        showNextUnit();
      }
    }
    // 输入模式下不处理Enter和空格键，避免自动提交
  }, [isInputMode, isWaitingForNext, isBusy, showNextUnit]);

  const handleInputKeyPress = useCallback((event: React.KeyboardEvent) => {
    // 只处理Tab键，Enter键不自动提交
    if (event.key === 'Tab') {
      event.preventDefault();
      if (defaultReply && !isUsingDefaultReply) {
        setPlayerInput(defaultReply);
        setIsUsingDefaultReply(true);
      }
    }
    // 移除Enter键的自动提交逻辑
  }, [defaultReply, isUsingDefaultReply]);

  const handleClick = useCallback(() => {
    if (isInputMode) return;
    if (isWaitingForNext && !isBusy) {
      showNextUnit();
    }
  }, [isInputMode, isWaitingForNext, isBusy, showNextUnit]);

  // === Effects ===

  useEffect(() => {
    if (!isGameStarted) {
      startNewGame();
    }
  }, [isGameStarted, startNewGame]);

  // Bind keyboard events
  useEffect(() => {
    document.addEventListener('keydown', handleKeyPress);
    return () => {
      document.removeEventListener('keydown', handleKeyPress);
    };
  }, [handleKeyPress]);

  // Debug: 监控状态变化
  useEffect(() => {
    console.log('状态变化:', {
      isWaitingForNext,
      isBusy,
      isInputMode,
      currentUnitIndex,
      scriptLength: currentScript.length,
      currentDisplay: currentDisplay?.content?.substring(0, 30) + '...'
    });
  }, [isWaitingForNext, isBusy, isInputMode, currentUnitIndex, currentScript.length, currentDisplay]);

  // === Render Helpers ===

  const renderGameState = () => {
    if (!gameState) return null;

    return (
      <div className="fixed top-20 right-4 bg-black bg-opacity-50 p-2 rounded text-xs text-white">
        <div>偏差值: {gameState.deviation.toFixed(1)}</div>
        <div>回合: {turnNumber}</div>
        <div>章节: {currentAnchor?.chapter_id || 0}-{currentAnchor?.anchor_index || 0}</div>
      </div>
    );
  };

  // === Main Render ===

  return (
    <div className="galgame-container" onClick={handleClick}>
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
            title="返回主菜单"
            onClick={onBack}
          >
            <X size={16} />
            <span>返回</span>
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

      {/* 游戏状态显示 */}
      {renderGameState()}

      {/* 背景全屏展示区 */}
      <div className="background-layer">
        <div className="background-image">
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
        {isInputMode ? (
          <div className="dialogue-container">
            <div className="name-box">
              <span className="character-name">选择输入</span>
            </div>
            <div className="dialogue-box">
              <div className="input-area">
                <p className="dialogue-text mb-2">{currentDisplay?.content}</p>
                <div className="input-controls">
                  <input
                    ref={inputRef}
                    type="text"
                    value={playerInput}
                    onChange={(e) => {
                      setPlayerInput(e.target.value);
                      setIsUsingDefaultReply(false);
                    }}
                    onKeyPress={handleInputKeyPress}
                    placeholder={defaultReply ? `推荐回答: ${defaultReply} (按Tab键使用)` : "输入您的选择..."}
                    disabled={isBusy}
                    className="player-input"
                    style={{
                      width: '100%',
                      padding: '8px',
                      border: '1px solid #ccc',
                      borderRadius: '4px',
                      fontSize: '14px',
                      backgroundColor: isUsingDefaultReply ? '#f0f0f0' : '#ffffff',
                      color: '#000000',
                      opacity: isUsingDefaultReply ? 0.8 : 1
                    }}
                  />
                  <button
                    onClick={handlePlayerSubmit}
                    disabled={!playerInput.trim() || isBusy}
                    className="submit-btn"
                    style={{
                      marginLeft: '8px',
                      padding: '8px 16px',
                      backgroundColor: '#007bff',
                      color: 'white',
                      border: 'none',
                      borderRadius: '4px',
                      cursor: 'pointer'
                    }}
                  >
                    提交
                  </button>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="dialogue-container">
            <div className="name-box">
              <span className="character-name">{getCharacterName()}</span>
            </div>
            <div className="dialogue-box">
              {error ? (
                <p className="dialogue-text" style={{color: 'red'}}>❌ {error}</p>
              ) : !isGameStarted ? (
                <p className="dialogue-text">🎮 正在启动 AI 交互式故事...</p>
              ) : (
                <div>
                  <p className="dialogue-text">{getDialogueText()}</p>
                  {isWaitingForNext && (
                    <div className="mt-2 text-sm text-gray-400 animate-pulse">
                      点击屏幕或按 Enter 继续...
                    </div>
                  )}
                  {isBusy && (
                    <div className="mt-2 text-sm text-blue-400">
                      🤖 AI 正在思考...
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* 操作按钮区 */}
      <div className="control-panel">
        <div className="control-left">
          {showOptions && (
            <div className="choice-buttons">
              <button className="choice-btn" onClick={() => setShowOptions(false)}>
                关闭选项
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
            {dialogueHistory.map((item, index) => (
              <div key={index} className="backlog-item">
                <div className="backlog-name">{item.name}</div>
                <div className="backlog-text">{item.text}</div>
              </div>
            ))}
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
  );
};

export default InteractiveGameReader;