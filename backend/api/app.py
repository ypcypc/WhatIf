from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import extraction, game
from api.routes.config import router as config_router
from api.routes.voice import router as voice_router

app = FastAPI(
    title="WhatIf API",
    description="WhatIf 互动式小说引擎 API",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(game.router)
app.include_router(extraction.router)
app.include_router(config_router)
app.include_router(voice_router)


@app.get("/api/health")
async def health_check():
    return {"status": "ok"}
