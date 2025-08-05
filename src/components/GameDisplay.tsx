/**
 * Game Display Component - 2025 React Pattern
 * 
 * Modern features:
 * - No local state management
 * - External store subscription
 * - Keyboard event handling with modern patterns
 * - Responsive design with Tailwind
 */

import React, { useEffect } from 'react';
import { 
  useScriptDisplay, 
  usePlayerActions, 
  useGameControls, 
  useCharacterName,
  useGameState 
} from '../hooks/useGameStore';
import { GlassDialogueBox } from './GlassDialogueBox';

interface GameDisplayProps {
  onBack?: () => void;
}

export const GameDisplay: React.FC<GameDisplayProps> = ({ onBack }) => {
  const { 
    currentScript, 
    currentUnitIndex, 
    currentDisplay, 
    isWaitingForNext, 
    isProcessing,
    showNextUnit,
    scriptLength 
  } = useScriptDisplay();

  const { 
    isInputMode, 
    defaultReply, 
    processPlayerChoice 
  } = usePlayerActions();

  const { handleKeyPress, handleClick } = useGameControls();
  const { characterName, dialogueText } = useCharacterName();
  const { deviation, turnNumber } = useGameState();

  // Bind keyboard events
  useEffect(() => {
    document.addEventListener('keydown', handleKeyPress);
    return () => {
      document.removeEventListener('keydown', handleKeyPress);
    };
  }, [handleKeyPress]);

  // Handle player input submission
  const handlePlayerSubmit = (input: string) => {
    if (!input.trim() || isProcessing) return;
    processPlayerChoice(input.trim());
  };

  return (
    <div 
      className="min-h-screen bg-gradient-to-br from-purple-900 via-blue-900 to-indigo-900 relative overflow-hidden cursor-pointer"
      onClick={handleClick}
    >
      {/* Background Image */}
      <div 
        className="absolute inset-0 bg-cover bg-center opacity-30"
        style={{
          backgroundImage: 'url(/bg.jpg)',
        }}
      />

      {/* Game UI Container */}
      <div className="relative z-10 flex flex-col h-screen">
        {/* Header with Game Status */}
        <div className="flex justify-between items-center p-4 bg-black/20">
          <div className="text-white/70 text-sm">
            回合: {turnNumber} | 偏离度: {deviation?.toFixed(1)}%
          </div>
          <div className="text-white/70 text-sm">
            脚本进度: {currentUnitIndex + 1}/{scriptLength}
          </div>
          {onBack && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onBack();
              }}
              className="text-white/70 hover:text-white transition-colors"
            >
              返回主菜单
            </button>
          )}
        </div>

        {/* Main Game Area */}
        <div className="flex-1 flex flex-col justify-end p-4">
          {/* Character Sprite Area */}
          <div className="flex-1 flex items-center justify-center mb-8">
            <div className="text-white/20 text-6xl">
              👤
            </div>
          </div>

          {/* Dialogue Box */}
          <div className="max-w-4xl mx-auto w-full">
            <GlassDialogueBox
              characterName={characterName}
              dialogueText={dialogueText}
              isWaitingForInput={isInputMode}
              isProcessing={isProcessing}
              defaultReply={defaultReply}
              onSubmit={handlePlayerSubmit}
              showContinueHint={isWaitingForNext && !isInputMode}
            />
          </div>
        </div>

        {/* Processing Indicator */}
        {isProcessing && (
          <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2">
            <div className="bg-black/50 backdrop-blur-sm rounded-lg p-6 text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-white mx-auto mb-4"></div>
              <p className="text-white">处理中...</p>
            </div>
          </div>
        )}

        {/* Debug Info (Development only) */}
        {process.env.NODE_ENV === 'development' && currentDisplay && (
          <div className="absolute top-4 right-4 bg-black/50 backdrop-blur-sm rounded-lg p-4 max-w-sm">
            <h3 className="text-white font-bold mb-2">调试信息</h3>
            <div className="text-white/70 text-sm space-y-1">
              <p>类型: {currentDisplay.type}</p>
              <p>说话者: {currentDisplay.speaker || 'N/A'}</p>
              <p>输入模式: {isInputMode ? '是' : '否'}</p>
              <p>等待下一个: {isWaitingForNext ? '是' : '否'}</p>
              <p>处理中: {isProcessing ? '是' : '否'}</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};