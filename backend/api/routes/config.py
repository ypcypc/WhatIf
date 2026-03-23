import zipfile

from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel

import config
from api.deps import list_worldpkgs, load_worldpkg, get_current_wpkg_name
from config import (
    get_all_llm_configs,
    reload_llm_configs,
    set_api_key,
    get_provider_status,
    _PROVIDER_KEY_MAP,
)

router = APIRouter(prefix="/api/config", tags=["config"])


class ApiKeysRequest(BaseModel):
    keys: dict[str, str]


class TestKeyRequest(BaseModel):
    provider: str
    key: str


@router.get("/llm")
def get_llm_config_all():
    configs = get_all_llm_configs()
    result: dict[str, dict] = {"extractors": {}, "agents": {}}
    extractor_names = {
        "event_extractor", "lorebook_extractor", "decision_text_extractor",
        "necessity_grader", "transition_annotator", "cross_validator", "repairer",
    }
    for name, cfg in configs.items():
        section = "extractors" if name in extractor_names else "agents"
        result[section][name] = {
            "model": cfg.model,
            "temperature": cfg.temperature,
            "thinking_budget": cfg.thinking_budget,
        }
    return result


@router.put("/llm")
def update_llm_config(body: dict):
    try:
        reload_llm_configs(body)
    except (ValueError, Exception) as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"status": "ok"}


@router.get("/providers")
def get_providers():
    return get_provider_status()


@router.put("/api-keys")
def update_api_keys(body: ApiKeysRequest):
    errors = []
    for provider, key in body.keys.items():
        try:
            set_api_key(provider, key)
        except ValueError as e:
            errors.append(str(e))
    if errors:
        raise HTTPException(status_code=400, detail="; ".join(errors))
    return {"status": "ok"}


@router.post("/test-key")
async def test_key(body: TestKeyRequest):
    import os
    import asyncio
    env_var = _PROVIDER_KEY_MAP.get(body.provider)
    if not env_var:
        raise HTTPException(status_code=400, detail=f"未知 provider: {body.provider}")

    _MODEL_MAP = {
        "dashscope": "dashscope/qwen3.5-flash",
        "openai": "openai/gpt-4o-mini",
        "anthropic": "anthropic/claude-haiku-4-5-20251001",
        "gemini": "gemini/gemini-2.0-flash",
        "volcengine": "volcengine/doubao-1-5-lite-32k",
    }

    old_key = os.getenv(env_var)
    os.environ[env_var] = body.key
    try:
        from core.llm import LLMClient
        client = LLMClient()
        model = _MODEL_MAP.get(body.provider, f"{body.provider}/test")
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: client.generate(
            prompt="hi",
            model=model,
            temperature=0,
            log=False,
        ))
        return {"status": "ok", "message": "连接成功"}
    except Exception as e:
        if old_key:
            os.environ[env_var] = old_key
        else:
            os.environ.pop(env_var, None)
        raise HTTPException(status_code=400, detail=f"连接失败: {str(e)}")


# --- WorldPkg ---

class LoadWorldPkgRequest(BaseModel):
    filename: str


@router.get("/worldpkgs")
def get_worldpkgs():
    return {
        "packages": list_worldpkgs(),
        "current": get_current_wpkg_name(),
    }


@router.post("/worldpkg/load")
def load_worldpkg_endpoint(body: LoadWorldPkgRequest):
    try:
        load_worldpkg(body.filename)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"status": "ok", "loaded": body.filename}


@router.get("/worldpkg/cover/{filename}")
def get_worldpkg_cover(filename: str):
    """Serve cover image from a .wpkg zip (cover.png/jpg/webp at root)."""
    wpkg_path = config.OUTPUT_DIR / filename
    if not wpkg_path.exists() or wpkg_path.suffix != ".wpkg":
        raise HTTPException(404, "数据包不存在")
    _COVER_NAMES = {"cover.png": "image/png", "cover.jpg": "image/jpeg", "cover.jpeg": "image/jpeg", "cover.webp": "image/webp"}
    try:
        with zipfile.ZipFile(wpkg_path, "r") as zf:
            for name, media_type in _COVER_NAMES.items():
                if name in zf.namelist():
                    return Response(content=zf.read(name), media_type=media_type)
    except zipfile.BadZipFile:
        raise HTTPException(400, "损坏的 .wpkg 文件")
    raise HTTPException(404, "该数据包没有封面图片")


@router.post("/worldpkg/import")
async def import_worldpkg(file: UploadFile):
    if not file.filename or not file.filename.endswith(".wpkg"):
        raise HTTPException(400, "只接受 .wpkg 文件")
    dest = config.OUTPUT_DIR / file.filename
    if dest.exists():
        raise HTTPException(409, "同名数据包已存在")
    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    content = await file.read()
    dest.write_bytes(content)
    return {"status": "ok", "filename": file.filename}
