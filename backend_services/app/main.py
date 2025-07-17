"""
FastAPI Main Application for WhatIf AI Galgame Backend Services

Integrates multiple microservices:
- dict_service: Dictionary and text segment retrieval
- llm_service: LLM generation and chain processing  
- save_service: Game state management and persistence
- anchor_service: Anchor-based text assembly and extraction
"""

from fastapi import FastAPI
from app.core.config import settings
from app.core.middleware import setup_middleware

# Import service routers
from app.services.dict_service.routers import router as dict_router
from app.services.llm_service.routers import router as llm_router  
from app.services.save_service.routers import router as save_router
from app.services.anchor_service.routers import router as anchor_router
from app.services.game_router import router as game_router

# Create FastAPI application
app = FastAPI(
    title="WhatIf AI Galgame Backend Services",
    description="Multi-service backend for AI-powered visual novel game",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Setup middleware (CORS, logging, error handlers)
setup_middleware(app)

# Register service routers
app.include_router(dict_router, prefix="/api/v1")
app.include_router(llm_router, prefix="/api/v1") 
app.include_router(save_router, prefix="/api/v1")
app.include_router(anchor_router, prefix="/api/v1")
app.include_router(game_router)  # Game router has its own prefix

@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "message": "WhatIf AI Galgame Backend Services", 
        "version": "0.1.0",
        "services": ["dict_service", "llm_service", "save_service", "anchor_service", "game_service"]
    }

@app.get("/health")
async def health_check():
    """Detailed health check."""
    return {"status": "healthy", "services": "operational"}
