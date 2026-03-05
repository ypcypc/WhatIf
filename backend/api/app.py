from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import extraction, game

app = FastAPI(
    title="WhatIf API",
    description="WhatIf 互动式小说引擎 API",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(game.router)
app.include_router(extraction.router)


@app.get("/api/health")
async def health_check():
    return {"status": "ok"}
