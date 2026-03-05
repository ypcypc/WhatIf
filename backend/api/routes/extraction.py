from fastapi import APIRouter

router = APIRouter(prefix="/api/extraction", tags=["extraction"])


@router.get("/status")
async def extraction_status():
    return {"status": "not_started"}


@router.post("/start")
async def start_extraction():
    return {"message": "Extraction API not yet implemented"}
