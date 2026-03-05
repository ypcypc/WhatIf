import asyncio
import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from api.deps import get_engine
from api.schemas import (
    EventInfo,
    GameStateResponse,
    MessageResponse,
    NarrativeResponse,
    SaveListResponse,
)
from runtime.game import GameEngine

router = APIRouter(prefix="/api/game", tags=["game"])


class ActionRequest(BaseModel):
    action: str = Field(..., min_length=1)


class LoadRequest(BaseModel):
    slot: int


class SaveRequest(BaseModel):
    slot: int
    description: str = ""


def _state_event(engine: GameEngine) -> str:
    snap = engine.response_state
    return json.dumps({
        "phase": snap.phase,
        "eventId": snap.event_id,
        "turn": snap.turn,
        "awaitingNextEvent": snap.awaiting_next_event,
        "gameEnded": snap.game_ended,
    }, ensure_ascii=False)


@router.post("/start")
async def start_game(engine: GameEngine = Depends(get_engine)):

    async def event_stream():
        loop = asyncio.get_event_loop()
        chunk_queue: asyncio.Queue[str | None] = asyncio.Queue()

        def on_chunk(text: str) -> None:
            loop.call_soon_threadsafe(chunk_queue.put_nowait, text)

        future = loop.run_in_executor(None, engine.new_game, on_chunk)

        while not future.done():
            try:
                chunk = await asyncio.wait_for(chunk_queue.get(), timeout=0.1)
                data = json.dumps({"text": chunk}, ensure_ascii=False)
                yield f"event: chunk\ndata: {data}\n\n"
            except asyncio.TimeoutError:
                continue

        try:
            await future
        except Exception as e:
            err = json.dumps({"message": str(e)}, ensure_ascii=False)
            yield f"event: error\ndata: {err}\n\n"
            yield f"event: done\ndata: {{}}\n\n"
            return

        while not chunk_queue.empty():
            chunk = chunk_queue.get_nowait()
            data = json.dumps({"text": chunk}, ensure_ascii=False)
            yield f"event: chunk\ndata: {data}\n\n"

        yield f"event: state\ndata: {_state_event(engine)}\n\n"
        yield f"event: done\ndata: {{}}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/action")
async def player_action(
    request: ActionRequest,
    engine: GameEngine = Depends(get_engine),
):

    async def event_stream():
        loop = asyncio.get_event_loop()
        chunk_queue: asyncio.Queue[str | None] = asyncio.Queue()

        def on_chunk(text: str) -> None:
            loop.call_soon_threadsafe(chunk_queue.put_nowait, text)

        engine.on_narrative_chunk = on_chunk

        future = loop.run_in_executor(
            None, engine.process_input, request.action
        )

        while not future.done():
            try:
                chunk = await asyncio.wait_for(chunk_queue.get(), timeout=0.1)
                data = json.dumps({"text": chunk}, ensure_ascii=False)
                yield f"event: chunk\ndata: {data}\n\n"
            except asyncio.TimeoutError:
                continue

        try:
            await future
        except Exception as e:
            err = json.dumps({"message": str(e)}, ensure_ascii=False)
            yield f"event: error\ndata: {err}\n\n"
            yield f"event: done\ndata: {{}}\n\n"
            return

        while not chunk_queue.empty():
            chunk = chunk_queue.get_nowait()
            data = json.dumps({"text": chunk}, ensure_ascii=False)
            yield f"event: chunk\ndata: {data}\n\n"

        engine.on_narrative_chunk = None

        yield f"event: state\ndata: {_state_event(engine)}\n\n"
        yield f"event: done\ndata: {{}}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/continue")
async def continue_game(engine: GameEngine = Depends(get_engine)):

    async def event_stream():
        loop = asyncio.get_event_loop()
        chunk_queue: asyncio.Queue[str | None] = asyncio.Queue()

        def on_chunk(text: str) -> None:
            loop.call_soon_threadsafe(chunk_queue.put_nowait, text)

        future = loop.run_in_executor(None, engine.continue_game, on_chunk)

        while not future.done():
            try:
                chunk = await asyncio.wait_for(chunk_queue.get(), timeout=0.1)
                data = json.dumps({"text": chunk}, ensure_ascii=False)
                yield f"event: chunk\ndata: {data}\n\n"
            except asyncio.TimeoutError:
                continue

        try:
            await future
        except Exception as e:
            err = json.dumps({"message": str(e)}, ensure_ascii=False)
            yield f"event: error\ndata: {err}\n\n"
            yield f"event: done\ndata: {{}}\n\n"
            return

        while not chunk_queue.empty():
            chunk = chunk_queue.get_nowait()
            data = json.dumps({"text": chunk}, ensure_ascii=False)
            yield f"event: chunk\ndata: {data}\n\n"

        yield f"event: state\ndata: {_state_event(engine)}\n\n"
        yield f"event: done\ndata: {{}}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/state", response_model=GameStateResponse)
async def game_state(engine: GameEngine = Depends(get_engine)):
    snap = engine.response_state
    event_info = None
    if snap.event_id:
        event = engine.world.get_event(snap.event_id)
        if event:
            event_info = EventInfo(
                id=event.id,
                decision_text=event.decision_text,
                goal=event.goal,
                importance=event.importance.value,
                type=event.type,
            )

    return GameStateResponse(
        phase=snap.phase,
        event=event_info,
        turn=snap.turn,
        player_name=engine.player_name or None,
        awaiting_next_event=snap.awaiting_next_event,
        game_ended=snap.game_ended,
    )


@router.post("/save", response_model=MessageResponse)
async def save_game(
    request: SaveRequest,
    engine: GameEngine = Depends(get_engine),
):
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None, engine.save_game, request.slot, request.description
    )
    return MessageResponse(message=result)


@router.get("/saves", response_model=SaveListResponse)
async def list_saves(engine: GameEngine = Depends(get_engine)):
    return SaveListResponse(saves=engine.list_saves())


@router.post("/load", response_model=NarrativeResponse)
async def load_game(
    request: LoadRequest,
    engine: GameEngine = Depends(get_engine),
):
    loop = asyncio.get_event_loop()
    text = await loop.run_in_executor(None, engine.load_game, request.slot)
    snap = engine.response_state
    return NarrativeResponse(
        text=text,
        phase=snap.phase,
        event_id=snap.event_id,
        turn=snap.turn,
    )
