/**
 * Game Initializer Component - 2025 React Pattern
 * 
 * Using modern patterns:
 * - No useEffect for initialization
 * - External store subscription
 * - Automatic initialization on render
 * - Error boundaries and suspense-ready
 */

import React, { useEffect } from 'react';
import { useGameInitialization, useGameError } from '../hooks/useGameStore';

interface GameInitializerProps {
  children: React.ReactNode;
  onError?: (error: string) => void;
}

export const GameInitializer: React.FC<GameInitializerProps> = ({ 
  children, 
  onError 
}) => {
  const { isInitialized, isProcessing, initializeGame } = useGameInitialization();
  const { error, hasError } = useGameError();

  // Auto-initialize game on mount (idempotent)
  useEffect(() => {
    if (!isInitialized && !isProcessing) {
      console.log('Auto-initializing game...');
      initializeGame();
    }
  }, [isInitialized, isProcessing, initializeGame]);

  // Handle errors
  useEffect(() => {
    if (hasError && onError) {
      onError(error!);
    }
  }, [hasError, error, onError]);

  // Show loading state during initialization
  if (isProcessing && !isInitialized) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-purple-900 via-blue-900 to-indigo-900">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-white mx-auto mb-4"></div>
          <p className="text-white text-lg">正在初始化游戏...</p>
        </div>
      </div>
    );
  }

  // Show error state
  if (hasError) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-red-900 via-purple-900 to-indigo-900">
        <div className="text-center bg-black/30 backdrop-blur-sm rounded-lg p-8 max-w-md">
          <div className="text-red-400 text-6xl mb-4">⚠️</div>
          <h2 className="text-white text-xl font-bold mb-4">游戏初始化失败</h2>
          <p className="text-red-200 mb-6 whitespace-pre-line">{error}</p>
          <button
            onClick={initializeGame}
            className="bg-red-600 hover:bg-red-700 text-white px-6 py-2 rounded-lg transition-colors"
          >
            重试
          </button>
        </div>
      </div>
    );
  }

  // Show loading state if not initialized
  if (!isInitialized) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-purple-900 via-blue-900 to-indigo-900">
        <div className="text-center">
          <div className="animate-pulse">
            <div className="h-4 bg-white/20 rounded w-48 mb-4"></div>
            <div className="h-4 bg-white/20 rounded w-32 mx-auto"></div>
          </div>
          <p className="text-white/70 mt-4">准备开始游戏...</p>
        </div>
      </div>
    );
  }

  // Render children when initialized
  return <>{children}</>;
};