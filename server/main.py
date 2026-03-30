"""서버 진입점. 등록/초기화/해제만 — 로직 금지."""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from server.api.chat import router as chat_router
from server.api.websocket import router as ws_router
from server.config.constants import (
    API_HOST,
    API_PORT,
    EXECUTOR_MODEL_FILE,
    LLAMA_BIN,
    MODELS_DIR,
    ROUTER_MODEL_FILE,
)
from server.domain.queue_processor import run_worker, stop_worker
from server.system.process_manager import start_all, stop_all

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

app = FastAPI(title="Dual-Model LLM Server", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)
app.include_router(ws_router)

_worker_task: asyncio.Task | None = None


@app.on_event("startup")
async def startup():
    global _worker_task

    models_dir = Path(MODELS_DIR)
    router_path = str(models_dir / ROUTER_MODEL_FILE)
    executor_path = str(models_dir / EXECUTOR_MODEL_FILE)

    start_all(
        router_model=router_path,
        executor_model=executor_path,
        llama_bin=LLAMA_BIN,
    )

    _worker_task = asyncio.create_task(run_worker())


@app.on_event("shutdown")
async def shutdown():
    stop_worker()
    if _worker_task:
        _worker_task.cancel()
    stop_all()


if __name__ == "__main__":
    uvicorn.run("server.main:app", host=API_HOST, port=API_PORT, reload=True)
