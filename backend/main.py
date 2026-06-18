import asyncio, logging
from contextlib import asynccontextmanager
import aiosqlite, uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator
from bot import WanderOnBot
from db import init_db, get_db_path
from llm import PROVIDERS
from security import valid_tg_token

logging.basicConfig(level=logging.INFO, format="[WanderOn] %(asctime)s — %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("wanderon")

_bot: WanderOnBot | None = None
_task: asyncio.Task | None = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    log.info("Backend ready on http://127.0.0.1:7291")
    yield
    if _bot:
        await _bot.stop()

app = FastAPI(title="WanderOn", lifespan=lifespan)
app.add_middleware(CORSMiddleware,
    allow_origins=["tauri://localhost", "http://localhost:1420", "http://127.0.0.1:1420"],
    allow_methods=["GET", "POST", "DELETE"], allow_headers=["Content-Type"])

class Config(BaseModel):
    telegram_token: str
    llm_provider: str
    llm_api_key: str
    llm_model: str
    otm_key: str = ""
    owm_key: str = ""
    er_key: str = ""
    serpapi_key: str = ""   # Google Hotels real data

    @field_validator("telegram_token")
    @classmethod
    def chk_token(cls, v):
        if not valid_tg_token(v.strip()):
            raise ValueError("Invalid Telegram token format")
        return v.strip()

    @field_validator("llm_provider")
    @classmethod
    def chk_provider(cls, v):
        if v.lower() not in PROVIDERS:
            raise ValueError(f"Unknown provider: {v}")
        return v.lower()

    @field_validator("llm_api_key")
    @classmethod
    def chk_key(cls, v, info):
        if info.data.get("llm_provider") == "ollama":
            return v or "local"
        if not v.strip() or len(v.strip()) < 8:
            raise ValueError("API key too short")
        return v.strip()

@app.get("/health")
async def health():
    return {"ok": True}

@app.post("/configure")
async def configure(cfg: Config):
    global _bot, _task
    if _task and not _task.done():
        await _bot.stop()
        _task.cancel()
        try:
            await _task
        except asyncio.CancelledError:
            pass
    try:
        _bot = WanderOnBot(
            cfg.telegram_token, cfg.llm_provider, cfg.llm_api_key, cfg.llm_model,
            cfg.otm_key, cfg.owm_key, cfg.er_key, cfg.serpapi_key
        )
        _task = asyncio.create_task(_bot.run())
        await asyncio.sleep(0.8)
        if _task.done() and _task.exception():
            raise _task.exception()
        return {"success": True}
    except Exception as e:
        _bot = None
        log.error(f"Bot start failed: {e}")
        raise HTTPException(400, str(e))

@app.get("/status")
async def status():
    if not _bot:
        return {"bot_running": False, "provider": "", "model": "", "username": "", "vision": False, "serpapi": False}
    return {
        "bot_running": _bot.running,
        "provider":    _bot.llm_provider,
        "model":       _bot.llm_model,
        "username":    _bot.bot_username or "",
        "vision":      _bot.planner.vision_ok(),
        "serpapi":     bool(_bot.planner.serpapi_key),
    }

@app.post("/stop")
async def stop():
    global _bot, _task
    if _bot:
        await _bot.stop()
        if _task:
            _task.cancel()
        _bot = None
    return {"success": True}

@app.get("/trips")
async def trips():
    async with aiosqlite.connect(get_db_path()) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM trips ORDER BY created_at DESC LIMIT 50") as c:
            return [dict(r) for r in await c.fetchall()]

@app.delete("/trips/{tid}")
async def del_trip(tid: int):
    async with aiosqlite.connect(get_db_path()) as db:
        await db.execute("DELETE FROM trips WHERE id=?", (tid,))
        await db.commit()
    return {"success": True}

@app.delete("/trips")
async def clear_trips():
    async with aiosqlite.connect(get_db_path()) as db:
        await db.execute("DELETE FROM trips")
        await db.commit()
    return {"success": True}

@app.get("/providers")
async def providers():
    return {k: {"models": v["models"], "vision": v["vision"]} for k, v in PROVIDERS.items()}

if __name__ == "__main__":
    import sys
    port = 7291
    for arg in sys.argv[1:]:
        if arg.startswith("--port="):
            port = int(arg.split("=")[1])
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")