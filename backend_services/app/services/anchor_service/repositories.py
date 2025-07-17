"""
Repository layer for anchor service.

This module provides pure data access functionality without business logic.
The AnchorRepository class handles all JSON file operations for text chunks.
"""

import json
import os
from typing import List, Dict, Any, Optional
from pathlib import Path
from app.core.utils import ensure_data_file_exists


class AnchorRepository:
    """
    Repository for anchor-related data access operations.
    
    Provides methods for:
    1. Getting chapter first chunk
    2. Batch fetching chunks in range
    3. Single chunk text retrieval
    
    Data source: data/article_data.json
    """
    
    def __init__(self, data_path: str = None):
        """
        Initialize repository with JSON data file.
        
        Args:
            data_path: Path to the article data JSON file
        """
        if data_path is None:
            # 使用工具函数获取数据文件路径
            self.data_path = ensure_data_file_exists("article_data.json")
        else:
            self.data_path = Path(data_path)
        
        self._data_cache: Optional[List[Dict[str, Any]]] = None
        self._load_data()
    
    def _load_data(self) -> None:
        """Load article data from JSON file."""
        try:
            with open(self.data_path, 'r', encoding='utf-8') as f:
                self._data_cache = json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Article data file not found: {self.data_path}")
        except json.JSONDecodeError:
            raise ValueError(f"Invalid JSON format in: {self.data_path}")
    
    def _get_chapter_data(self, chapter_id: int) -> Optional[Dict[str, Any]]:
        """Get chapter data by ID."""
        if not self._data_cache:
            return None
        
        for chapter in self._data_cache:
            if chapter.get('id') == chapter_id:
                return chapter
        return None
    
    def _get_chunk_data(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        """Get chunk data by ID across all chapters."""
        if not self._data_cache:
            return None
        
        for chapter in self._data_cache:
            for chunk in chapter.get('chunks', []):
                if chunk.get('chunk_id') == chunk_id:
                    return {
                        'chapter_id': chapter.get('id'),
                        'chunk_id': chunk.get('chunk_id'),
                        'text': chunk.get('text', '')
                    }
        return None

    def get_first_chunk_id(self, chapter_id: int) -> str:
        """
        Get the first chunk ID for a given chapter.
        
        Args:
            chapter_id: Chapter identifier
            
        Returns:
            First chunk ID in the chapter (first in chunks array)
            
        Raises:
            ValueError: If no chunks found for the chapter
        """
        chapter_data = self._get_chapter_data(chapter_id)
        if not chapter_data:
            raise ValueError(f"No chapter found with ID {chapter_id}")
        
        chunks = chapter_data.get('chunks', [])
        if not chunks:
            raise ValueError(f"No chunks found for chapter {chapter_id}")
        
        return chunks[0]['chunk_id']

    def get_chunks_in_range(
        self, 
        *, 
        chapter_id: int, 
        start_id: str, 
        end_id: str
    ) -> List[str]:
        """
        Batch fetch chunk texts within a specified range.
        
        Args:
            chapter_id: Chapter identifier
            start_id: Starting chunk ID (inclusive)
            end_id: Ending chunk ID (inclusive)
            
        Returns:
            List of text content in the specified range, ordered by chunk position
        """
        chapter_data = self._get_chapter_data(chapter_id)
        if not chapter_data:
            return []
        
        chunks = chapter_data.get('chunks', [])
        if not chunks:
            return []
        
        # Find start and end indices
        start_idx = None
        end_idx = None
        
        for i, chunk in enumerate(chunks):
            if chunk['chunk_id'] == start_id:
                start_idx = i
            if chunk['chunk_id'] == end_id:
                end_idx = i
        
        if start_idx is None or end_idx is None:
            return []
        
        # Extract text from the range
        result = []
        for i in range(start_idx, end_idx + 1):
            result.append(chunks[i]['text'])
        
        return result

    def get_chunk_text(self, chunk_id: str) -> str:
        """
        Get text content for a single chunk.
        
        Args:
            chunk_id: Chunk identifier
            
        Returns:
            Text content of the chunk, empty string if not found
        """
        chunk_data = self._get_chunk_data(chunk_id)
        if not chunk_data:
            return ""
        
        return chunk_data.get('text', '')

    def chunk_exists(self, chunk_id: str) -> bool:
        """
        Check if a chunk exists in the data.
        
        Args:
            chunk_id: Chunk identifier
            
        Returns:
            True if chunk exists, False otherwise
        """
        return self._get_chunk_data(chunk_id) is not None

    def get_chapter_chunk_count(self, chapter_id: int) -> int:
        """
        Get total number of chunks in a chapter.
        
        Args:
            chapter_id: Chapter identifier
            
        Returns:
            Number of chunks in the chapter
        """
        chapter_data = self._get_chapter_data(chapter_id)
        if not chapter_data:
            return 0
        
        return len(chapter_data.get('chunks', []))

    def get_all_chapters(self) -> List[Dict[str, Any]]:
        """
        Get all chapters metadata.
        
        Returns:
            List of chapter dictionaries with id, title, etc.
        """
        if not self._data_cache:
            return []
        
        return [
            {
                'id': chapter.get('id'),
                'title': chapter.get('title', ''),
                'chunk_count': len(chapter.get('chunks', []))
            }
            for chapter in self._data_cache
        ]
