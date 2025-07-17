"""
Save Service Data Access Layer

Handles data persistence for game saves and backups:
- SQLite database for save metadata
- File system for save data and backups
- JSON serialization and compression
"""

import json
import logging
import sqlite3
import zipfile
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from backend_services.app.core.config import settings
from .schemas import GameState, SaveInfo, BackupInfo

logger = logging.getLogger(__name__)


class SaveRepository:
    """
    Repository for save data stored in SQLite and file system.
    
    Manages:
    - Save metadata in SQLite
    - Game state serialization
    - Save slot management
    """
    
    def __init__(self):
        """Initialize repository with database and file paths."""
        self.db_path = Path(settings.database_url.replace("sqlite:///", ""))
        self.saves_dir = Path(settings.data_dir) / "saves"
        
        # Ensure directories exist
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.saves_dir.mkdir(parents=True, exist_ok=True)
        
        self._init_database()
    
    def _init_database(self):
        """Initialize database tables if they don't exist."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS saves (
                        slot_name TEXT PRIMARY KEY,
                        description TEXT,
                        chapter TEXT,
                        scene TEXT,
                        diff_score REAL,
                        play_time INTEGER,
                        save_count INTEGER DEFAULT 1,
                        file_path TEXT,
                        file_size INTEGER,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                conn.commit()
                logger.info("Save database initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize save database: {e}")
            raise
    
    async def save_game_state(
        self,
        slot_name: str,
        game_state: GameState,
        description: Optional[str] = None,
        screenshot: Optional[str] = None
    ) -> SaveInfo:
        """
        Save game state to file and database.
        
        Args:
            slot_name: Save slot identifier
            game_state: Game state to save
            description: Optional save description
            screenshot: Optional screenshot data
            
        Returns:
            SaveInfo with save metadata
        """
        try:
            # Prepare save data
            save_data = {
                "game_state": game_state.dict(),
                "description": description,
                "screenshot": screenshot,
                "saved_at": datetime.now().isoformat()
            }
            
            # Write to file
            save_file = self.saves_dir / f"{slot_name}.json"
            with open(save_file, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
            
            file_size = save_file.stat().st_size
            
            # Update database
            with sqlite3.connect(self.db_path) as conn:
                # Check if save exists to determine save count
                cursor = conn.execute(
                    "SELECT save_count FROM saves WHERE slot_name = ?",
                    (slot_name,)
                )
                existing = cursor.fetchone()
                save_count = existing[0] + 1 if existing else 1
                
                # Insert or update save metadata
                conn.execute("""
                    INSERT OR REPLACE INTO saves (
                        slot_name, description, chapter, scene, diff_score,
                        play_time, save_count, file_path, file_size, 
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 
                             COALESCE((SELECT created_at FROM saves WHERE slot_name = ?), CURRENT_TIMESTAMP),
                             CURRENT_TIMESTAMP)
                """, (
                    slot_name, description, game_state.chapter, game_state.scene,
                    game_state.diff_score, sum(game_state.variables.get("play_time", [0])),
                    save_count, str(save_file), file_size, slot_name
                ))
                
            conn.commit()
             
             # Return save info
            save_info = await self.get_save_info(slot_name)
            if not save_info:
                raise RuntimeError(f"Failed to retrieve save info after saving: {slot_name}")
            return save_info
            
        except Exception as e:
            logger.error(f"Failed to save game state: {e}")
            raise
    
    async def load_game_state(self, slot_name: str) -> Optional[GameState]:
        """
        Load game state from file.
        
        Args:
            slot_name: Save slot identifier
            
        Returns:
            GameState object or None if not found
        """
        try:
            save_file = self.saves_dir / f"{slot_name}.json"
            if not save_file.exists():
                return None
            
            with open(save_file, 'r', encoding='utf-8') as f:
                save_data = json.load(f)
            
            game_state_data = save_data.get("game_state", {})
            return GameState(**game_state_data)
            
        except Exception as e:
            logger.error(f"Failed to load game state from {slot_name}: {e}")
            return None
    
    async def get_save_info(self, slot_name: str) -> Optional[SaveInfo]:
        """
        Get save metadata from database.
        
        Args:
            slot_name: Save slot identifier
            
        Returns:
            SaveInfo object or None if not found
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    "SELECT * FROM saves WHERE slot_name = ?",
                    (slot_name,)
                )
                row = cursor.fetchone()
                
                if row:
                    return SaveInfo(
                        slot_name=row["slot_name"],
                        description=row["description"],
                        chapter=row["chapter"],
                        scene=row["scene"],
                        diff_score=row["diff_score"],
                        play_time=row["play_time"],
                        save_count=row["save_count"],
                        created_at=datetime.fromisoformat(row["created_at"]),
                        updated_at=datetime.fromisoformat(row["updated_at"]),
                        file_size=row["file_size"]
                    )
                return None
                
        except Exception as e:
            logger.error(f"Failed to get save info for {slot_name}: {e}")
            return None
    
    async def list_saves(self) -> List[SaveInfo]:
        """
        List all available saves.
        
        Returns:
            List of SaveInfo objects
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    "SELECT * FROM saves ORDER BY updated_at DESC"
                )
                
                saves = []
                for row in cursor.fetchall():
                    saves.append(SaveInfo(
                        slot_name=row["slot_name"],
                        description=row["description"],
                        chapter=row["chapter"],
                        scene=row["scene"],
                        diff_score=row["diff_score"],
                        play_time=row["play_time"],
                        save_count=row["save_count"],
                        created_at=datetime.fromisoformat(row["created_at"]),
                        updated_at=datetime.fromisoformat(row["updated_at"]),
                        file_size=row["file_size"]
                    ))
                
                return saves
                
        except Exception as e:
            logger.error(f"Failed to list saves: {e}")
            return []
    
    async def delete_save(self, slot_name: str) -> bool:
        """
        Delete save from database and file system.
        
        Args:
            slot_name: Save slot identifier
            
        Returns:
            True if deletion successful
        """
        try:
            # Delete from database
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "DELETE FROM saves WHERE slot_name = ?",
                    (slot_name,)
                )
                
                if cursor.rowcount == 0:
                    return False
                
                conn.commit()
            
            # Delete save file
            save_file = self.saves_dir / f"{slot_name}.json"
            if save_file.exists():
                save_file.unlink()
            
            logger.info(f"Deleted save slot: {slot_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete save {slot_name}: {e}")
            return False


class FileRepository:
    """
    Repository for file system operations.
    
    Handles:
    - Backup creation and restoration
    - File compression and decompression
    - Directory management
    """
    
    def __init__(self):
        """Initialize repository with file paths."""
        self.data_dir = Path(settings.data_dir)
        self.saves_dir = self.data_dir / "saves"
        self.backups_dir = self.data_dir / "backups"
        
        # Ensure directories exist
        for directory in [self.data_dir, self.saves_dir, self.backups_dir]:
            directory.mkdir(parents=True, exist_ok=True)
    
    async def create_backup(self, backup_id: str, save_slots: List[str]) -> str:
        """
        Create compressed backup of save files.
        
        Args:
            backup_id: Backup identifier
            save_slots: List of save slots to include
            
        Returns:
            Path to created backup file
        """
        try:
            backup_file = self.backups_dir / f"{backup_id}.zip"
            
            with zipfile.ZipFile(backup_file, 'w', zipfile.ZIP_DEFLATED) as zf:
                # Add save files
                for slot_name in save_slots:
                    save_file = self.saves_dir / f"{slot_name}.json"
                    if save_file.exists():
                        zf.write(save_file, f"saves/{slot_name}.json")
                
                # Add metadata
                metadata = {
                    "backup_id": backup_id,
                    "created_at": datetime.now().isoformat(),
                    "save_slots": save_slots,
                    "version": "1.0"
                }
                zf.writestr("backup_metadata.json", json.dumps(metadata, indent=2))
            
            logger.info(f"Created backup: {backup_file}")
            return str(backup_file)
            
        except Exception as e:
            logger.error(f"Failed to create backup {backup_id}: {e}")
            raise
    
    async def restore_backup(self, backup_id: str) -> bool:
        """
        Restore saves from backup file.
        
        Args:
            backup_id: Backup identifier
            
        Returns:
            True if restore successful
        """
        try:
            backup_file = self.backups_dir / f"{backup_id}.zip"
            if not backup_file.exists():
                return False
            
            with zipfile.ZipFile(backup_file, 'r') as zf:
                # Extract save files
                for file_info in zf.filelist:
                    if file_info.filename.startswith("saves/"):
                        zf.extract(file_info, self.data_dir)
            
            logger.info(f"Restored backup: {backup_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to restore backup {backup_id}: {e}")
            return False
    
    async def list_backups(self) -> List[BackupInfo]:
        """
        List all available backup files.
        
        Returns:
            List of BackupInfo objects
        """
        try:
            backups = []
            
            for backup_file in self.backups_dir.glob("*.zip"):
                try:
                    with zipfile.ZipFile(backup_file, 'r') as zf:
                        # Read metadata
                        metadata_content = zf.read("backup_metadata.json")
                        metadata = json.loads(metadata_content)
                        
                        backups.append(BackupInfo(
                            backup_id=metadata["backup_id"],
                            save_slots=metadata["save_slots"],
                            created_at=datetime.fromisoformat(metadata["created_at"]),
                            file_size=backup_file.stat().st_size,
                            compressed=True
                        ))
                        
                except Exception as e:
                    logger.warning(f"Failed to read backup metadata from {backup_file}: {e}")
            
            return sorted(backups, key=lambda b: b.created_at, reverse=True)
            
        except Exception as e:
            logger.error(f"Failed to list backups: {e}")
            return []
    
    async def get_file_size(self, file_path: str) -> int:
        """
        Get file size in bytes.
        
        Args:
            file_path: Path to file
            
        Returns:
            File size in bytes
        """
        try:
            return Path(file_path).stat().st_size
        except Exception:
            return 0 