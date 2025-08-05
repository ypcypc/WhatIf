/**
 * Interactive Game Reader - 2025 React Pattern
 * 
 * Modern features:
 * - External store with useSyncExternalStore
 * - GameInitializer for proper initialization
 * - GameDisplay for game rendering
 * - No local state management
 */

import React from 'react';
import { GameInitializer } from './GameInitializer';
import { GameDisplay } from './GameDisplay';

interface InteractiveGameReaderProps {
  onBack?: () => void;
}

const InteractiveGameReader: React.FC<InteractiveGameReaderProps> = ({ onBack }) => {
  const handleError = (error: string) => {
    console.error('Game initialization error:', error);
    // Could show a toast notification or error modal here
  };

  return (
    <GameInitializer onError={handleError}>
      <GameDisplay onBack={onBack} />
    </GameInitializer>
  );
};

export default InteractiveGameReader;