import React, { useState, useEffect, useCallback } from 'react';
import { getFirstChunk, getNextChunk } from '../services/anchorService';
import type { ChunkResponse } from '../services/anchorService';
import './GameReader.css';

interface GameReaderProps {
  onBack: () => void;
}

const GameReader: React.FC<GameReaderProps> = ({ onBack }) => {
  const [currentChunk, setCurrentChunk] = useState<ChunkResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isWaitingForNext, setIsWaitingForNext] = useState(false);
  const [history, setHistory] = useState<ChunkResponse[]>([]);

  // 获取下一个文本块
  const getNext = useCallback(async () => {
    if (isLoading || !currentChunk) return;
    
    setIsLoading(true);
    setError(null);
    setIsWaitingForNext(false);

    try {
      if (currentChunk.is_last_overall) {
        setError('已到达故事结尾');
        return;
      }

      const nextChunk = await getNextChunk(currentChunk.chunk_id);
      setCurrentChunk(nextChunk);
      setHistory(prev => [...prev, nextChunk]);
      setIsWaitingForNext(true);
    } catch (err) {
      console.error('获取下一段失败:', err);
      setError(err instanceof Error ? err.message : '获取下一段失败');
    } finally {
      setIsLoading(false);
    }
  }, [currentChunk, isLoading]);

  // 处理键盘事件
  const handleKeyPress = useCallback((event: KeyboardEvent) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      if (isWaitingForNext && !isLoading) {
        getNext();
      }
    }
  }, [isWaitingForNext, isLoading, getNext]);

  // 处理点击事件
  const handleClick = useCallback(() => {
    if (isWaitingForNext && !isLoading) {
      getNext();
    }
  }, [isWaitingForNext, isLoading, getNext]);

  // 初始化 - 获取第一个文本块
  useEffect(() => {
    const initializeReader = async () => {
      setIsLoading(true);
      setError(null);

      try {
        const firstChunk = await getFirstChunk();
        setCurrentChunk(firstChunk);
        setHistory([firstChunk]);
        setIsWaitingForNext(true);
      } catch (err) {
        console.error('初始化失败:', err);
        setError(err instanceof Error ? err.message : '初始化失败');
      } finally {
        setIsLoading(false);
      }
    };

    initializeReader();
  }, []);

  // 绑定键盘事件
  useEffect(() => {
    document.addEventListener('keydown', handleKeyPress);
    return () => {
      document.removeEventListener('keydown', handleKeyPress);
    };
  }, [handleKeyPress]);

  // 获取角色名称（简单的逻辑）
  const getCharacterName = (text: string, chunkId: string): string => {
    // 如果是第一个块，通常是标题
    if (chunkId === 'ch1_1') return '章节标题';
    
    // 简单的角色识别逻辑
    if (text.includes('我') || text.includes('三上悟')) {
      return '三上悟';
    }
    
    return '旁白';
  };

  return (
    <div className="galgame-container" onClick={handleClick}>
      {/* 顶部状态栏 */}
      <div className="top-status-bar">
        <div className="status-left">
          <button 
            className="status-btn" 
            title="返回主菜单"
            onClick={onBack}
          >
            <span>← 返回</span>
          </button>
        </div>
        <div className="status-right">
          <span className="text-sm text-gray-600">
            {currentChunk ? `第${currentChunk.chapter_id}章 - ${currentChunk.chunk_id}` : '加载中...'}
          </span>
        </div>
      </div>

      {/* 背景全屏展示区 */}
      <div className="background-layer">
        <div className="background-image">
          <div className="background-placeholder">
            <span>背景图片区域</span>
          </div>
        </div>
        <div className="background-overlay"></div>
      </div>

      {/* CG画面/角色立绘层 */}
      <div className="content-layer">
        <div className="cg-area">
          <div className="cg-placeholder">
            <span>CG 大图区域</span>
          </div>
        </div>
        <div className="sprite-area">
          <div className="character-sprite">
            <div className="sprite-placeholder">
              <span>角色立绘层</span>
            </div>
          </div>
        </div>
      </div>

      {/* 对话框区域 */}
      <div className="dialogue-panel">
        <div className="dialogue-container">
          <div className="name-box">
            <span className="character-name">
              {currentChunk ? getCharacterName(currentChunk.text, currentChunk.chunk_id) : '加载中...'}
            </span>
          </div>
          <div className="dialogue-box">
            {isLoading ? (
              <p className="dialogue-text">加载中...</p>
            ) : error ? (
              <p className="dialogue-text text-red-500">{error}</p>
            ) : currentChunk ? (
              <div>
                <p className="dialogue-text">{currentChunk.text}</p>
                {isWaitingForNext && !currentChunk.is_last_overall && (
                  <div className="mt-2 text-sm text-gray-400 animate-pulse">
                    点击屏幕或按 Enter 继续...
                  </div>
                )}
                {currentChunk.is_last_overall && (
                  <div className="mt-2 text-sm text-blue-400">
                    故事结束
                  </div>
                )}
              </div>
            ) : (
              <p className="dialogue-text">准备开始...</p>
            )}
          </div>
        </div>
      </div>

      {/* 调试信息 */}
      {currentChunk && (
        <div className="fixed bottom-2 left-2 text-xs text-gray-500 bg-black bg-opacity-50 p-2 rounded">
          <div>当前块: {currentChunk.chunk_id}</div>
          <div>章节末: {currentChunk.is_last_in_chapter ? '是' : '否'}</div>
          <div>故事末: {currentChunk.is_last_overall ? '是' : '否'}</div>
          {currentChunk.next_chunk_id && (
            <div>下一块: {currentChunk.next_chunk_id}</div>
          )}
        </div>
      )}
    </div>
  );
};

export default GameReader;
