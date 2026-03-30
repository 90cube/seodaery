"""llama-server 프로세스 관리. 시작/종료/헬스체크만 담당한다."""

from __future__ import annotations

import asyncio
import logging
import subprocess
import sys
from pathlib import Path

from server.config.constants import (
    EXECUTOR_CTX_SIZE,
    EXECUTOR_GPU_LAYERS,
    EXECUTOR_MODEL_URL,
    ROUTER_CTX_SIZE,
    ROUTER_GPU_LAYERS,
    ROUTER_MODEL_URL,
)

logger = logging.getLogger(__name__)

_processes: dict[str, subprocess.Popen] = {}


def _extract_port(url: str) -> str:
    return url.rsplit(":", 1)[-1]


def start_model(
    name: str,
    model_path: str,
    base_url: str,
    ctx_size: int,
    gpu_layers: int,
    llama_bin: str = "llama-server",
) -> subprocess.Popen | None:
    """llama-server 프로세스를 시작한다."""
    if not Path(model_path).exists():
        logger.error("모델 파일 없음: %s", model_path)
        return None

    port = _extract_port(base_url)
    cmd = [
        llama_bin,
        "--model", model_path,
        "--ctx-size", str(ctx_size),
        "--n-gpu-layers", str(gpu_layers),
        "--port", port,
        "--host", "127.0.0.1",
    ]

    logger.info("시작: %s (port %s)", name, port)
    logger.info("명령: %s", " ".join(cmd))

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    _processes[name] = proc
    return proc


def start_all(
    router_model: str,
    executor_model: str,
    llama_bin: str = "llama-server",
) -> None:
    """라우터 + 실행기 두 프로세스를 모두 시작한다."""
    start_model(
        name="router",
        model_path=router_model,
        base_url=ROUTER_MODEL_URL,
        ctx_size=ROUTER_CTX_SIZE,
        gpu_layers=ROUTER_GPU_LAYERS,
        llama_bin=llama_bin,
    )
    start_model(
        name="executor",
        model_path=executor_model,
        base_url=EXECUTOR_MODEL_URL,
        ctx_size=EXECUTOR_CTX_SIZE,
        gpu_layers=EXECUTOR_GPU_LAYERS,
        llama_bin=llama_bin,
    )


def stop_all() -> None:
    """실행 중인 모든 llama-server 프로세스를 종료한다."""
    for name, proc in _processes.items():
        if proc.poll() is None:
            logger.info("종료: %s (pid %d)", name, proc.pid)
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
    _processes.clear()


def is_running(name: str) -> bool:
    """특정 프로세스가 살아 있는지 확인한다."""
    proc = _processes.get(name)
    return proc is not None and proc.poll() is None
