"""서버 진입점. 등록/초기화/해제만 — 로직 금지."""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from server.api.chat import router as chat_router
from server.api.debug import router as debug_router
from server.api.event import router as event_router
from server.api.websocket import router as ws_router
from server.config.constants import (
    API_HOST,
    API_PORT,
    EXECUTOR_MODEL_FILE,
    LIGHT_MODEL_FILE,
    LLAMA_BIN,
    MODELS_DIR,
)
from server.domain.event_tool_handlers import (
    handle_create_schedule,
    handle_list_schedules,
)
from server.domain.queue_processor import run_worker, stop_worker
from server.domain.tool_executor import register_executor
from server.system.process_manager import start_all_models, stop_all

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

app = FastAPI(title="서대리 LLM Server", version="0.3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)
app.include_router(debug_router)
app.include_router(event_router)
app.include_router(ws_router)

_static_dir = Path(__file__).resolve().parent / "static"
if _static_dir.is_dir():
    app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")

_worker_task: asyncio.Task | None = None


@app.on_event("startup")
async def startup():
    global _worker_task

    models_dir = Path(MODELS_DIR)
    executor_path = str(models_dir / EXECUTOR_MODEL_FILE)
    light_path = str(models_dir / LIGHT_MODEL_FILE)

    await start_all_models(
        executor_model=executor_path,
        light_model=light_path,
        llama_bin=LLAMA_BIN,
    )

    register_executor("create_schedule", handle_create_schedule)
    register_executor("list_schedules", handle_list_schedules)

    _worker_task = asyncio.create_task(run_worker())


@app.on_event("shutdown")
async def shutdown():
    stop_worker()
    if _worker_task:
        _worker_task.cancel()
    stop_all()


if __name__ == "__main__":
    uvicorn.run("server.main:app", host=API_HOST, port=API_PORT, reload=True)
