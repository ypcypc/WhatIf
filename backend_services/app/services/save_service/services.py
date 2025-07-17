"""
Save Service Business Logic

Handles game state management, save/load operations, and backup functionality.
Coordinates between repositories and file system operations.
"""

import logging
from typing import List
from datetime import datetime

from .repositories import SaveRepository, FileRepository
from .schemas import SaveRequest, SaveResponse, LoadResponse, SaveInfo, BackupInfo

logger = logging.getLogger(__name__)


class SaveService:
    """
    Save service for handling game state persistence and management.
    
    Provides high-level business logic for:
    - Game state saving and loading
    - Save slot management
    - Backup and restore operations
    """
    
    def __init__(self):
        """Initialize service with repositories."""
        self.save_repo = SaveRepository()
        self.file_repo = FileRepository()
    
    async def save_game(self, request: SaveRequest) -> SaveResponse:
        """
        Save game state to specified slot.
        
        Args:
            request: Save request with game state and metadata
            
        Returns:
            SaveResponse with operation result
        """
        logger.info(f"Saving game to slot: {request.slot_name}")
        
        try:
            # Validate game state
            if not request.game_state.anchor:
                raise ValueError("Invalid game state: missing anchor")
            
            # Save to repository
            save_info = await self.save_repo.save_game_state(
                slot_name=request.slot_name,
                game_state=request.game_state,
                description=request.description,
                screenshot=request.screenshot
            )
            
            return SaveResponse(
                success=True,
                slot_name=request.slot_name,
                message=f"游戏已保存到槽位 {request.slot_name}",
                save_info=save_info
            )
            
        except Exception as e:
            logger.error(f"Save failed for slot {request.slot_name}: {e}")
            return SaveResponse(
                success=False,
                slot_name=request.slot_name,
                message=f"保存失败: {str(e)}",
                                 save_info=SaveInfo(
                     slot_name=request.slot_name,
                     description=None,
                     chapter="",
                     scene="",
                     diff_score=0.0,
                     play_time=0,
                     save_count=0,
                     created_at=datetime.now(),
                     updated_at=datetime.now(),
                     file_size=0
                 )
            )
    
    async def load_game(self, slot_name: str) -> LoadResponse:
        """
        Load game state from specified slot.
        
        Args:
            slot_name: Save slot identifier
            
        Returns:
            LoadResponse with game state and metadata
            
        Raises:
            ValueError: If save slot not found
        """
        logger.info(f"Loading game from slot: {slot_name}")
        
        # Check if save exists
        save_info = await self.save_repo.get_save_info(slot_name)
        if not save_info:
            raise ValueError(f"Save slot not found: {slot_name}")
        
        # Load game state
        game_state = await self.save_repo.load_game_state(slot_name)
        if not game_state:
            raise ValueError(f"Failed to load game state from slot: {slot_name}")
        
        return LoadResponse(
            game_state=game_state,
            save_info=save_info
        )
    
    async def delete_save(self, slot_name: str) -> bool:
        """
        Delete save from specified slot.
        
        Args:
            slot_name: Save slot identifier
            
        Returns:
            True if deletion successful, False otherwise
        """
        logger.info(f"Deleting save slot: {slot_name}")
        
        try:
            return await self.save_repo.delete_save(slot_name)
        except Exception as e:
            logger.error(f"Delete failed for slot {slot_name}: {e}")
            return False
    
    async def list_saves(self) -> List[SaveInfo]:
        """
        List all available save slots.
        
        Returns:
            List of save slot information
        """
        logger.info("Listing all save slots")
        
        try:
            return await self.save_repo.list_saves()
        except Exception as e:
            logger.error(f"Failed to list saves: {e}")
            return []
    
    async def create_backup(self) -> BackupInfo:
        """
        Create backup of all save data.
        
        Returns:
            Backup information
        """
        logger.info("Creating backup of all saves")
        
        try:
            # Get all saves
            saves = await self.save_repo.list_saves()
            save_slots = [save.slot_name for save in saves]
            
            # Create backup
            backup_id = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            backup_path = await self.file_repo.create_backup(backup_id, save_slots)
            
            # Get backup file size
            file_size = await self.file_repo.get_file_size(backup_path)
            
            return BackupInfo(
                backup_id=backup_id,
                save_slots=save_slots,
                created_at=datetime.now(),
                file_size=file_size,
                compressed=True
            )
            
        except Exception as e:
            logger.error(f"Backup creation failed: {e}")
            raise
    
    async def restore_backup(self, backup_id: str) -> bool:
        """
        Restore saves from backup.
        
        Args:
            backup_id: Backup identifier
            
        Returns:
            True if restore successful, False otherwise
        """
        logger.info(f"Restoring backup: {backup_id}")
        
        try:
            return await self.file_repo.restore_backup(backup_id)
        except Exception as e:
            logger.error(f"Backup restore failed for {backup_id}: {e}")
            return False
    
    async def list_backups(self) -> List[BackupInfo]:
        """
        List all available backups.
        
        Returns:
            List of backup information
        """
        logger.info("Listing all backups")
        
        try:
            return await self.file_repo.list_backups()
        except Exception as e:
            logger.error(f"Failed to list backups: {e}")
            return []
    
    async def get_save_statistics(self) -> dict:
        """
        Get save system statistics.
        
        Returns:
            Dictionary with save statistics
        """
        try:
            saves = await self.save_repo.list_saves()
            backups = await self.file_repo.list_backups()
            
            total_size = sum(save.file_size for save in saves)
            total_play_time = sum(save.play_time for save in saves)
            
            return {
                "total_saves": len(saves),
                "total_backups": len(backups),
                "total_size_bytes": total_size,
                "total_play_time_seconds": total_play_time,
                "most_recent_save": max(saves, key=lambda s: s.updated_at).slot_name if saves else None,
                "oldest_save": min(saves, key=lambda s: s.created_at).slot_name if saves else None
            }
            
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {} 