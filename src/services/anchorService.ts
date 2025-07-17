/**
 * Anchor Service API Client
 * 
 * This module provides functions to interact with the anchor_service backend.
 */

// API base URL - adjust according to your backend setup
const API_BASE_URL = 'http://localhost:8000/api/v1/anchor';

// Type definitions matching the backend models
export interface Anchor {
  node_id: string;
  chunk_id: string;
  chapter_id: number;
}

export interface AssembleRequest {
  anchors: Anchor[];
  include_chapter_intro: boolean;
}

export interface Span {
  chapter_id: number;
  start_id: string;
  end_id: string;
  text: string;
}

export interface AssembleResponse {
  text: string;
  spans: Span[];
}

export interface ValidationResponse {
  valid: boolean;
  errors: string[];
  stats: {
    total_anchors: number;
    unique_chapters: number;
    estimated_spans: number;
    chapter_sequence: number[];
  };
}

export interface ChunkResponse {
  chunk_id: string;
  chapter_id: number;
  text: string;
  is_last_in_chapter: boolean;
  is_last_overall: boolean;
  next_chunk_id: string | null;
}

export interface NextChunkRequest {
  current_chunk_id: string;
}

export interface AnchorContextRequest {
  current_anchor: Anchor;
  previous_anchor?: Anchor;
  include_tail: boolean;
  is_last_anchor_in_chapter: boolean;
}

export interface AnchorContextResponse {
  context: string;
  current_anchor: Anchor;
  context_stats: {
    total_length: number;
    has_prefix: boolean;
    has_tail: boolean;
    chunks_included: number;
    previous_anchor_provided: boolean;
    include_tail_requested: boolean;
    is_last_anchor_in_chapter: boolean;
  };
}

/**
 * Assemble text from anchor points
 */
export async function assembleText(request: AssembleRequest): Promise<AssembleResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/assemble`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(`HTTP ${response.status}: ${errorData.detail?.message || response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Error assembling text:', error);
    throw error;
  }
}

/**
 * Validate anchor points without assembling text
 */
export async function validateAnchors(request: AssembleRequest): Promise<ValidationResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/validate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(`HTTP ${response.status}: ${errorData.detail?.message || response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Error validating anchors:', error);
    throw error;
  }
}

/**
 * Health check for anchor service
 */
export async function healthCheck(): Promise<{ status: string; service: string; version: string }> {
  try {
    const response = await fetch(`${API_BASE_URL}/health`);

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Error checking health:', error);
    throw error;
  }
}

/**
 * Get the first chunk of the story
 */
export async function getFirstChunk(): Promise<ChunkResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/chunk/first`);

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(`HTTP ${response.status}: ${errorData.detail?.message || response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Error getting first chunk:', error);
    throw error;
  }
}

/**
 * Get a specific chunk by ID
 */
export async function getChunk(chunkId: string): Promise<ChunkResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/chunk/${encodeURIComponent(chunkId)}`);

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(`HTTP ${response.status}: ${errorData.detail?.message || response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Error getting chunk:', error);
    throw error;
  }
}

/**
 * Get the next chunk in sequence
 */
export async function getNextChunk(currentChunkId: string): Promise<ChunkResponse> {
  try {
    const request: NextChunkRequest = {
      current_chunk_id: currentChunkId
    };

    const response = await fetch(`${API_BASE_URL}/chunk/next`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(`HTTP ${response.status}: ${errorData.detail?.message || response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Error getting next chunk:', error);
    throw error;
  }
}

/**
 * Build context for a specific anchor
 */
export async function buildAnchorContext(request: AnchorContextRequest): Promise<AnchorContextResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/context`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(`HTTP ${response.status}: ${errorData.detail?.message || response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Error building anchor context:', error);
    throw error;
  }
}
