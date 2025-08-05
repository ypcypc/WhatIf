/**
 * Game Service API Client
 * 
 * This module provides functions to interact with the complete game API
 * that coordinates Anchor Service and LLM Service according to CLAUDE.md specifications.
 */

// API base URL - use environment variable or fallback
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

// === Type Definitions ===

export interface ScriptUnit {
  type: 'narration' | 'dialogue' | 'interaction';
  content: string;
  speaker?: string;
  choice_id?: string;
  default_reply?: string;
  metadata?: Record<string, any>;
}

export interface GameState {
  deviation: number;
  affinity: Record<string, number>;
  flags: Record<string, boolean>;
  variables: Record<string, any>;
}

export interface GameStartRequest {
  session_id: string;
  protagonist?: string;
  chapter_id?: number;
  anchor_index?: number;
}

export interface GameStartResponse {
  session_id: string;
  script: ScriptUnit[];
  context: string;
  current_anchor: {
    node_id: string;
    chapter_id: number;
    chunk_id: string;
  };
  game_state: GameState;
  turn_number: number;
  message: string;
}

export interface GameTurnRequest {
  session_id: string;
  chapter_id: number;
  anchor_index: number;
  player_choice: string;
  previous_anchor_index?: number;
  include_tail?: boolean;
  is_last_anchor_in_chapter?: boolean;
  current_anchor_id?: string; // Add storyline-based anchor ID
}

export interface GameTurnResponse {
  session_id: string;
  script: ScriptUnit[];
  updated_state: GameState;
  turn_number: number;
  context_used: string;
  anchor_info: {
    chapter_id: number;
    anchor_index: number;
    chunk_id: string;
    current_anchor_id: string;
    next_anchor_id: string | null;
    context_stats: Record<string, any>;
  };
  generation_metadata: Record<string, any>;
}

export interface SessionStatus {
  session_id: string;
  status: string;
  protagonist: string;
  created_at: string;
  last_active: string;
  turn_count: number;
}

// === API Functions ===

/**
 * Start a new game session
 */
export async function startGame(request: GameStartRequest, signal?: AbortSignal): Promise<GameStartResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/game/start`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        session_id: request.session_id,
        protagonist: request.protagonist || 'c_san_shang_wu',
        chapter_id: request.chapter_id || 1,
        anchor_index: request.anchor_index || 0
      }),
      signal, // Add abort signal support
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(`HTTP ${response.status}: ${errorData.detail?.message || response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Error starting game:', error);
    throw error;
  }
}

/**
 * Process a complete game turn
 */
export async function processTurn(request: GameTurnRequest, signal?: AbortSignal): Promise<GameTurnResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/game/turn`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
      signal, // Add abort signal support
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(`HTTP ${response.status}: ${errorData.detail?.message || response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Error processing turn:', error);
    throw error;
  }
}

/**
 * Get session status
 */
export async function getSessionStatus(sessionId: string): Promise<SessionStatus> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/game/sessions/${encodeURIComponent(sessionId)}/status`);

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(`HTTP ${response.status}: ${errorData.detail?.message || response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Error getting session status:', error);
    throw error;
  }
}

/**
 * Health check for game service
 */
export async function gameHealthCheck(): Promise<{ status: string; components: any }> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/game/health`);

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Error checking game health:', error);
    throw error;
  }
}

// === Helper Functions ===

/**
 * Generate a unique session ID
 */
export function generateSessionId(): string {
  const timestamp = Date.now();
  const random = Math.random().toString(36).substr(2, 9);
  return `session_${timestamp}_${random}`;
}

/**
 * Parse script units for rendering
 */
export function parseScriptForRendering(script: ScriptUnit[]): {
  narrativeUnits: ScriptUnit[];
  dialogueUnits: ScriptUnit[];
  interactionUnits: ScriptUnit[];
} {
  return {
    narrativeUnits: script.filter(unit => unit.type === 'narration'),
    dialogueUnits: script.filter(unit => unit.type === 'dialogue'),
    interactionUnits: script.filter(unit => unit.type === 'interaction')
  };
}

/**
 * Validate game state
 */
export function validateGameState(state: GameState): boolean {
  return (
    typeof state.deviation === 'number' &&
    state.deviation >= 0 &&
    state.deviation <= 100 &&
    typeof state.affinity === 'object' &&
    typeof state.flags === 'object' &&
    typeof state.variables === 'object'
  );
}