/**
 * External Game Store - 2025 React Pattern
 * 
 * Following modern patterns:
 * - External state management outside React
 * - useSyncExternalStore integration
 * - Promise-based async operations
 * - Subscription pattern for reactive updates
 */

import { startGame, processTurn, type GameStartRequest, type GameTurnRequest, type GameStartResponse, type GameTurnResponse, type ScriptUnit, type GameState } from '../services/gameService';

// Game store state interface
interface GameStoreState {
  sessionId: string | null;
  isInitialized: boolean;
  isProcessing: boolean;
  gameState: GameState | null;
  currentScript: ScriptUnit[];
  currentUnitIndex: number;
  turnNumber: number;
  currentAnchor: { chapter_id: number; anchor_index: number; anchor_id?: string } | null;
  error: string | null;
  
  // UI state
  currentDisplay: {
    type: 'narration' | 'dialogue' | 'interaction';
    content: string;
    speaker?: string;
    isPlayerChoice?: boolean;
  } | null;
  isWaitingForNext: boolean;
  isInputMode: boolean;
  defaultReply: string;
}

// Initial state
const initialState: GameStoreState = {
  sessionId: null,
  isInitialized: false,
  isProcessing: false,
  gameState: null,
  currentScript: [],
  currentUnitIndex: 0,
  turnNumber: 0,
  currentAnchor: null,
  error: null,
  currentDisplay: null,
  isWaitingForNext: false,
  isInputMode: false,
  defaultReply: '',
};

// Store class implementing 2025 external store pattern
class GameStore {
  private state: GameStoreState = { ...initialState };
  private listeners = new Set<() => void>();
  private abortController: AbortController | null = null;

  // Subscribe to store changes (for useSyncExternalStore)
  subscribe = (callback: () => void) => {
    this.listeners.add(callback);
    return () => this.listeners.delete(callback);
  };

  // Get current snapshot (for useSyncExternalStore)
  getSnapshot = () => this.state;

  // Get server snapshot (for SSR)
  getServerSnapshot = () => initialState;

  // Notify all subscribers of state change
  private notify = () => {
    this.listeners.forEach(callback => callback());
  };

  // Update state and notify subscribers
  private setState = (updates: Partial<GameStoreState>) => {
    this.state = { ...this.state, ...updates };
    this.notify();
  };

  // Generate unique session ID
  generateSessionId = (): string => {
    const timestamp = Date.now();
    const random = Math.random().toString(36).substr(2, 9);
    return `session_${timestamp}_${random}`;
  };

  // Initialize game session (idempotent operation)
  initializeGame = async (): Promise<void> => {
    // Idempotent check
    if (this.state.isInitialized || this.state.isProcessing) {
      console.log('Game already initialized or initializing');
      return;
    }

    // Cancel any existing operation
    this.abortController?.abort();
    this.abortController = new AbortController();

    const sessionId = this.generateSessionId();
    
    this.setState({
      sessionId,
      isProcessing: true,
      error: null,
    });

    try {
      console.log('Initializing game with session:', sessionId);
      
      const response: GameStartResponse = await startGame({
        session_id: sessionId,
        protagonist: 'c_san_shang_wu',
        chapter_id: 1,
        anchor_index: 0,
      }, this.abortController.signal);

      // Only update if not aborted
      if (!this.abortController.signal.aborted) {
        console.log('Game initialized successfully:', response);
        
        this.setState({
          isInitialized: true,
          isProcessing: false,
          gameState: response.game_state,
          currentScript: response.script,
          turnNumber: response.turn_number,
          currentAnchor: {
            chapter_id: response.current_anchor.chapter_id,
            anchor_index: 0,
            anchor_id: response.current_anchor.node_id, // Store storyline-based anchor ID
          },
          currentUnitIndex: 0,
        });

        // Start script display
        this.displayUnit(0);
      }
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
        console.log('Game initialization aborted');
        return;
      }

      if (!this.abortController.signal.aborted) {
        console.error('Failed to initialize game:', error);
        this.setState({
          isProcessing: false,
          error: error instanceof Error ? error.message : 'Game initialization failed',
        });
      }
    }
  };

  // Display current script unit
  displayUnit = (index: number) => {
    const { currentScript } = this.state;
    
    if (index >= currentScript.length) {
      console.log('Reached script end');
      this.setState({
        isProcessing: false,
        isWaitingForNext: true,
      });
      return;
    }

    const unit = currentScript[index];
    console.log(`Displaying unit ${index + 1}/${currentScript.length}: ${unit.type}`);

    this.setState({
      currentUnitIndex: index,
      currentDisplay: {
        type: unit.type,
        content: unit.content,
        speaker: unit.speaker,
      },
    });

    // Handle interaction units
    if (unit.type === 'interaction') {
      this.setState({
        isInputMode: true,
        isWaitingForNext: false,
        isProcessing: false,
        defaultReply: unit.default_reply || '',
      });
    } else {
      this.setState({
        isWaitingForNext: true,
        isProcessing: false,
      });
    }
  };

  // Show next unit in script
  showNextUnit = () => {
    if (this.state.isProcessing || this.state.isInputMode) return;
    
    const nextIndex = this.state.currentUnitIndex + 1;
    this.displayUnit(nextIndex);
  };

  // Process player turn with modern async pattern
  processPlayerTurn = async (playerChoice: string): Promise<void> => {
    const { currentAnchor, sessionId } = this.state;
    
    if (!currentAnchor || !sessionId || this.state.isProcessing) {
      return;
    }

    // Cancel any existing operation
    this.abortController?.abort();
    this.abortController = new AbortController();

    this.setState({
      isProcessing: true,
      isInputMode: false,
      isWaitingForNext: false,
      error: null,
      // Show player choice temporarily
      currentDisplay: {
        type: 'dialogue',
        content: playerChoice,
        speaker: '玩家',
        isPlayerChoice: true,
      },
    });

    try {
      console.log('Processing player turn:', playerChoice);

      // Process turn with backend  
      const turnRequest = {
        session_id: sessionId,
        chapter_id: currentAnchor.chapter_id,
        anchor_index: currentAnchor.anchor_index,
        player_choice: playerChoice,
        previous_anchor_index: currentAnchor.anchor_index > 0 ? currentAnchor.anchor_index - 1 : undefined,
        include_tail: false,
        is_last_anchor_in_chapter: false,
        current_anchor_id: currentAnchor.anchor_id, // Pass storyline-based anchor ID
      };
      
      console.log('🔍 FRONTEND TURN REQUEST DEBUG:', turnRequest);
      console.log('📍 Current anchor details:', currentAnchor);
      
      const response: GameTurnResponse = await processTurn(turnRequest, this.abortController.signal);

      // Only update if not aborted
      if (!this.abortController.signal.aborted) {
        console.log('Turn processed successfully:', response);

        // Check for fallback/error responses
        if (response.script.length < 5) {
          console.warn('Backend returned insufficient script units:', response.script.length);
          
          const hasError = response.script.some(unit => unit.metadata?.fallback);
          if (hasError) {
            const errorMsg = response.script.find(unit => unit.metadata?.error)?.metadata?.error || 'Unknown error';
            console.error('Backend LLM generation failed:', errorMsg);
            this.setState({
              error: `Story generation failed: ${errorMsg}`,
            });
          }
        }

        this.setState({
          gameState: response.updated_state,
          currentScript: response.script,
          turnNumber: response.turn_number,
          currentAnchor: {
            chapter_id: response.anchor_info.chapter_id,
            anchor_index: response.anchor_info.anchor_index,
            anchor_id: response.anchor_info.current_anchor_id, // Store updated anchor ID
          },
          currentUnitIndex: 0,
          isProcessing: false,
        });

        // Start new script display
        this.displayUnit(0);
      }
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
        console.log('Player turn processing aborted');
        return;
      }

      if (!this.abortController.signal.aborted) {
        console.error('Failed to process player turn:', error);
        this.setState({
          isProcessing: false,
          error: error instanceof Error ? error.message : 'Turn processing failed',
        });
      }
    }
  };

  // Reset store state
  reset = () => {
    this.abortController?.abort();
    this.abortController = null;
    this.state = { ...initialState };
    this.notify();
  };

  // Cleanup method
  cleanup = () => {
    this.abortController?.abort();
    this.listeners.clear();
  };
}

// Create singleton store instance
export const gameStore = new GameStore();

// Export types for use in components
export type { GameStoreState };