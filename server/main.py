"""서버 진입점. 등록/초기화/해제만 — 로직 금지."""

from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import sys
import webbrowser
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from server.api.chat import router as chat_router
from server.api.debug import router as debug_router
from server.api.event import router as event_router
from server.api.n8n import router as n8n_router
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
logger = logging.getLogger(__name__)

_worker_task: asyncio.Task | None = None
_client_proc: subprocess.Popen | None = None

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_CLIENT_SCRIPT = _PROJECT_ROOT / "client.py"


def _launch_client() -> None:
    """client.py를 새 터미널 창에서 실행한다."""
    global _client_proc
    if not _CLIENT_SCRIPT.exists():
        logger.warning("client.py 없음: %s", _CLIENT_SCRIPT)
        return
    try:
        if sys.platform == "win32":
            _client_proc = subprocess.Popen(
                ["cmd", "/c", "start", "서대리 클라이언트",
                 sys.executable, str(_CLIENT_SCRIPT)],
                cwd=str(_PROJECT_ROOT),
            )
        else:
            _client_proc = subprocess.Popen(
                [sys.executable, str(_CLIENT_SCRIPT)],
                cwd=str(_PROJECT_ROOT),
            )
        logger.info("client.py 실행 완료")
    except Exception as exc:
        logger.warning("client.py 실행 실패: %s", exc)


def _open_brain_map() -> None:
    """브라우저에서 brain_map.html을 연다."""
    url = f"http://{API_HOST}:{API_PORT}/static/brain_map.html"
    try:
        webbrowser.open(url)
        logger.info("Brain Map 열기: %s", url)
    except Exception as exc:
        logger.warning("브라우저 열기 실패: %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """서버 시작/종료 생명주기."""
    global _worker_task

    # -- startup --
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

    logger.info("모델 로드 완료 → Brain Map + 클라이언트 자동 실행")
    _open_brain_map()
    _launch_client()

    yield

    # -- shutdown --
    stop_worker()
    if _worker_task:
        _worker_task.cancel()
    if _client_proc and _client_proc.poll() is None:
        _client_proc.terminate()
    stop_all()


app = FastAPI(title="서대리 LLM Server", version="0.3.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)
app.include_router(debug_router)
app.include_router(event_router)
app.include_router(n8n_router)
app.include_router(ws_router)

_static_dir = Path(__file__).resolve().parent / "static"
if _static_dir.is_dir():
    app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")


if __name__ == "__main__":
    uvicorn.run("server.main:app", host=API_HOST, port=API_PORT, reload=True)
