"""
Save Service API Routes

Provides REST endpoints for:
- Game state saving and loading
- Save slot management
- Backup operations
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List

from .services import SaveService
from .schemas import SaveRequest, SaveResponse, LoadResponse, SaveInfo, BackupInfo

# Create router with prefix
router = APIRouter(prefix="/save", tags=["save"])

# Dependency injection
def get_save_service() -> SaveService:
    """Get save service instance."""
    return SaveService()

@router.post("/{slot_name}", response_model=SaveResponse)
async def save_game(
    slot_name: str,
    request: SaveRequest,
    save_service: SaveService = Depends(get_save_service)
) -> SaveResponse:
    """
    Save game state to specified slot.
    
    Args:
        slot_name: Save slot identifier
        request: Save request with game state
        
    Returns:
        SaveResponse with operation result
    """
    try:
        # Override slot name from URL
        request.slot_name = slot_name
        return await save_service.save_game(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Save operation failed")

@router.get("/{slot_name}", response_model=LoadResponse)
async def load_game(
    slot_name: str,
    save_service: SaveService = Depends(get_save_service)
) -> LoadResponse:
    """
    Load game state from specified slot.
    
    Args:
        slot_name: Save slot identifier
        
    Returns:
        LoadResponse with game state and metadata
    """
    try:
        return await save_service.load_game(slot_name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Load operation failed")

@router.delete("/{slot_name}")
async def delete_save(
    slot_name: str,
    save_service: SaveService = Depends(get_save_service)
) -> dict:
    """
    Delete save from specified slot.
    
    Args:
        slot_name: Save slot identifier
        
    Returns:
        Operation result
    """
    try:
        success = await save_service.delete_save(slot_name)
        if not success:
            raise HTTPException(status_code=404, detail="Save slot not found")
        return {"success": True, "message": f"Save slot {slot_name} deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Delete operation failed")

@router.get("/", response_model=List[SaveInfo])
async def list_saves(
    save_service: SaveService = Depends(get_save_service)
) -> List[SaveInfo]:
    """
    List all available save slots.
    
    Returns:
        List of save slot information
    """
    try:
        return await save_service.list_saves()
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to list saves")

@router.post("/backup")
async def create_backup(
    save_service: SaveService = Depends(get_save_service)
) -> BackupInfo:
    """
    Create backup of all save data.
    
    Returns:
        Backup information
    """
    try:
        return await save_service.create_backup()
    except Exception as e:
        raise HTTPException(status_code=500, detail="Backup creation failed")

@router.post("/restore/{backup_id}")
async def restore_backup(
    backup_id: str,
    save_service: SaveService = Depends(get_save_service)
) -> dict:
    """
    Restore saves from backup.
    
    Args:
        backup_id: Backup identifier
        
    Returns:
        Restore operation result
    """
    try:
        success = await save_service.restore_backup(backup_id)
        if not success:
            raise HTTPException(status_code=404, detail="Backup not found")
        return {"success": True, "message": f"Backup {backup_id} restored"}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Restore operation failed")

@router.get("/backup/list", response_model=List[BackupInfo])
async def list_backups(
    save_service: SaveService = Depends(get_save_service)
) -> List[BackupInfo]:
    """
    List all available backups.
    
    Returns:
        List of backup information
    """
    try:
        return await save_service.list_backups()
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to list backups") 