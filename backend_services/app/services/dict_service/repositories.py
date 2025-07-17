"""
Dictionary Service Data Access Layer

Handles data persistence and retrieval from various sources:
- SQLite database for anchor mappings
- File system for text content
- External dictionary APIs
"""

import asyncio
import logging
import sqlite3
import json
from pathlib import Path
from typing import List, Optional, Dict, Any

from backend_services.app.core.config import settings

logger = logging.getLogger(__name__)


class DictRepository:
    """
    Repository for dictionary and anchor data stored in SQLite.
    
    Manages:
    - Anchor to offset mappings
    - Dictionary entries cache
    - Content metadata
    """
    
    def __init__(self):
        """Initialize repository with database connection."""
        self.db_path = Path(settings.database_url.replace("sqlite:///", ""))
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """Initialize database tables if they don't exist."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS anchors (
                        anchor TEXT PRIMARY KEY,
                        chapter TEXT,
                        section TEXT,
                        start_offset INTEGER,
                        end_offset INTEGER,
                        source_file TEXT,
                        character_count INTEGER,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS dictionary_cache (
                        term TEXT PRIMARY KEY,
                        language TEXT,
                        definitions TEXT,  -- JSON array
                        pronunciation TEXT,
                        part_of_speech TEXT,
                        examples TEXT,     -- JSON array
                        cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                conn.commit()
                logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    async def get_anchor_info(self, anchor: str) -> Optional[Dict[str, Any]]:
        """
        Get anchor information from database.
        
        Args:
            anchor: Anchor identifier
            
        Returns:
            Anchor information dict or None if not found
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    "SELECT * FROM anchors WHERE anchor = ?", 
                    (anchor,)
                )
                row = cursor.fetchone()
                
                if row:
                    return dict(row)
                return None
        except Exception as e:
            logger.error(f"Error fetching anchor info for {anchor}: {e}")
            return None
    
    async def lookup_term(
        self, 
        term: str, 
        language: Optional[str] = "zh"
    ) -> Optional[Dict[str, Any]]:
        """
        Look up term in dictionary cache.
        
        Args:
            term: Term to look up
            language: Language code
            
        Returns:
            Dictionary entry or None if not found
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    "SELECT * FROM dictionary_cache WHERE term = ? AND language = ?",
                    (term, language)
                )
                row = cursor.fetchone()
                
                if row:
                    return {
                        "definitions": json.loads(row["definitions"] or "[]"),
                        "pronunciation": row["pronunciation"],
                        "part_of_speech": row["part_of_speech"],
                        "examples": json.loads(row["examples"] or "[]")
                    }
                return None
        except Exception as e:
            logger.error(f"Error looking up term {term}: {e}")
            return None
    
    async def list_anchors(self, chapter: Optional[str] = None) -> List[str]:
        """
        Get list of available anchors.
        
        Args:
            chapter: Optional chapter filter
            
        Returns:
            List of anchor identifiers
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                if chapter:
                    cursor = conn.execute(
                        "SELECT anchor FROM anchors WHERE chapter = ? ORDER BY anchor",
                        (chapter,)
                    )
                else:
                    cursor = conn.execute(
                        "SELECT anchor FROM anchors ORDER BY anchor"
                    )
                
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error listing anchors: {e}")
            return []


class FileSystemRepository:
    """
    Repository for file system access.
    
    Handles:
    - Reading text files
    - Content extraction by anchor
    - File metadata
    """
    
    def __init__(self):
        """Initialize repository with configured paths."""
        self.novels_dir = Path(settings.novels_dir)
        self.dictionaries_dir = Path(settings.dictionaries_dir)
        self.anchors_dir = Path(settings.anchors_dir)
        
        # Ensure directories exist
        for directory in [self.novels_dir, self.dictionaries_dir, self.anchors_dir]:
            directory.mkdir(parents=True, exist_ok=True)
    
    async def get_text_by_anchor(self, anchor: str) -> Optional[Dict[str, Any]]:
        """
        Get text content by anchor from file system.
        
        Args:
            anchor: Anchor identifier
            
        Returns:
            Text content with metadata or None if not found
        """
        # This is a simplified implementation
        # In reality, you would use the anchor to find the correct file and offset
        try:
            # For now, return a placeholder
            # You would implement actual file reading logic here
            return {
                "text": f"这是锚点 {anchor} 对应的文本内容示例。",
                "start_offset": 0,
                "end_offset": 50,
                "source_file": "example.txt",
                "language": "zh"
            }
        except Exception as e:
            logger.error(f"Error reading text for anchor {anchor}: {e}")
            return None
    
    async def read_file(self, file_path: str) -> Optional[str]:
        """
        Read text file content.
        
        Args:
            file_path: Path to file
            
        Returns:
            File content or None if error
        """
        try:
            path_obj = Path(file_path)
            if not path_obj.exists():
                return None
            
            with open(path_obj, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            return None 