/**
 * Modern React Hooks for Game Store - 2025 Patterns
 * 
 * Using:
 * - useSyncExternalStore for external state subscription
 * - React 19's useActionState for async actions
 * - Custom hooks for specific game functionality
 */

import { useSyncExternalStore, useCallback, startTransition } from 'react';
import { gameStore, type GameStoreState } from '../stores/gameStore';

// Main hook to subscribe to game store
export function useGameStore(): GameStoreState {
  return useSyncExternalStore(
    gameStore.subscribe,
    gameStore.getSnapshot,
    gameStore.getServerSnapshot
  );
}

// Hook for game initialization
export function useGameInitialization() {
  const { isInitialized, isProcessing, error } = useGameStore();

  const initializeGame = useCallback(() => {
    startTransition(() => {
      gameStore.initializeGame();
    });
  }, []);

  return {
    isInitialized,
    isProcessing,
    error,
    initializeGame,
  };
}

// Hook for script display control
export function useScriptDisplay() {
  const { 
    currentScript, 
    currentUnitIndex, 
    currentDisplay, 
    isWaitingForNext, 
    isProcessing 
  } = useGameStore();

  const showNextUnit = useCallback(() => {
    if (!isWaitingForNext || isProcessing) return;
    
    startTransition(() => {
      gameStore.showNextUnit();
    });
  }, [isWaitingForNext, isProcessing]);

  return {
    currentScript,
    currentUnitIndex,
    currentDisplay,
    isWaitingForNext,
    isProcessing,
    showNextUnit,
    scriptLength: currentScript.length,
  };
}

// Hook for player interactions
export function usePlayerActions() {
  const { isInputMode, defaultReply, isProcessing } = useGameStore();

  const processPlayerChoice = useCallback((choice: string) => {
    if (!choice.trim() || isProcessing) return;
    
    startTransition(() => {
      gameStore.processPlayerTurn(choice);
    });
  }, [isProcessing]);

  return {
    isInputMode,
    defaultReply,
    isProcessing,
    processPlayerChoice,
  };
}

// Hook for game state and metadata
export function useGameState() {
  const { gameState, turnNumber, currentAnchor, sessionId } = useGameStore();

  return {
    gameState,
    turnNumber,
    currentAnchor,
    sessionId,
    // Derived state
    deviation: gameState?.deviation ?? 0,
    affinity: gameState?.affinity ?? {},
    flags: gameState?.flags ?? {},
    variables: gameState?.variables ?? {},
  };
}

// Hook for character name derivation
export function useCharacterName() {
  const { currentDisplay } = useGameStore();

  const getCharacterName = useCallback((): string => {
    if (!currentDisplay) return '系统';
    
    if (currentDisplay.isPlayerChoice) return '玩家';
    if (currentDisplay.speaker) return currentDisplay.speaker;
    if (currentDisplay.type === 'narration') return '旁白';
    
    // Fallback character detection
    const content = currentDisplay.content;
    if (content.includes('三上悟') || content.includes('我')) {
      return '三上悟';
    }
    if (content.includes('你')) {
      return '主人公';
    }
    if (content.includes('"') || content.includes("'")) {
      return '对话';
    }
    return '系统';
  }, [currentDisplay]);

  const getDialogueText = useCallback((): string => {
    return currentDisplay?.content ?? '正在加载...';
  }, [currentDisplay]);

  return {
    characterName: getCharacterName(),
    dialogueText: getDialogueText(),
    currentDisplay,
  };
}

// Hook for keyboard and click handlers
export function useGameControls() {
  const { showNextUnit } = useScriptDisplay();
  const { isInputMode, isWaitingForNext, isProcessing } = useGameStore();

  const handleKeyPress = useCallback((event: KeyboardEvent) => {
    // Only handle Enter and Space when not in input mode
    if (!isInputMode && (event.key === 'Enter' || event.key === ' ')) {
      event.preventDefault();
      if (isWaitingForNext && !isProcessing) {
        showNextUnit();
      }
    }
  }, [isInputMode, isWaitingForNext, isProcessing, showNextUnit]);

  const handleClick = useCallback(() => {
    if (isInputMode) return;
    if (isWaitingForNext && !isProcessing) {
      showNextUnit();
    }
  }, [isInputMode, isWaitingForNext, isProcessing, showNextUnit]);

  return {
    handleKeyPress,
    handleClick,
  };
}

// Hook for error handling
export function useGameError() {
  const { error } = useGameStore();

  const clearError = useCallback(() => {
    // Could extend gameStore to have clearError method
    console.log('Clear error requested');
  }, []);

  return {
    error,
    hasError: !!error,
    clearError,
  };
}