"""llama-server 프로세스 관리. 시작/종료/헬스체크만 담당한다."""

from __future__ import annotations

import asyncio
import logging
import subprocess
from pathlib import Path

import httpx

from server.config.constants import (
    EXECUTOR_CTX_SIZE,
    EXECUTOR_GPU_LAYERS,
    EXECUTOR_MODEL_URL,
    KV_CACHE_DIR,
    LIGHT_CTX_SIZE,
    LIGHT_GPU_LAYERS,
    LIGHT_MODEL_URL,
)

logger = logging.getLogger(__name__)

_processes: dict[str, subprocess.Popen] = {}

HEALTH_CHECK_INTERVAL = 2.0
HEALTH_CHECK_MAX_WAIT = 180.0


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

    Path(KV_CACHE_DIR).mkdir(parents=True, exist_ok=True)

    port = _extract_port(base_url)
    cmd = [
        llama_bin,
        "--model", model_path,
        "--ctx-size", str(ctx_size),
        "--n-gpu-layers", str(gpu_layers),
        "--port", port,
        "--host", "127.0.0.1",
        "--slots",
        "--slot-save-path", KV_CACHE_DIR,
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


async def wait_until_ready(name: str, base_url: str) -> bool:
    """모델이 로딩 완료될 때까지 헬스체크로 대기한다."""
    logger.info("대기 중: %s 모델 로딩 (%s) ...", name, base_url)
    elapsed = 0.0

    while elapsed < HEALTH_CHECK_MAX_WAIT:
        proc = _processes.get(name)
        if proc and proc.poll() is not None:
            logger.error("%s 프로세스가 종료됨 (exit code: %d)", name, proc.returncode)
            return False

        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"{base_url}/health")
                if resp.status_code == 200:
                    logger.info("준비 완료: %s (%.1f초 소요)", name, elapsed)
                    return True
        except (httpx.RequestError, httpx.HTTPStatusError):
            pass

        await asyncio.sleep(HEALTH_CHECK_INTERVAL)
        elapsed += HEALTH_CHECK_INTERVAL

    logger.error("타임아웃: %s 모델 로딩 실패 (%.0f초 초과)", name, HEALTH_CHECK_MAX_WAIT)
    return False


async def start_executor_and_wait(
    executor_model: str,
    llama_bin: str = "llama-server",
) -> None:
    """실행기 프로세스를 시작하고 준비될 때까지 대기한다."""
    proc = start_model(
        name="executor",
        model_path=executor_model,
        base_url=EXECUTOR_MODEL_URL,
        ctx_size=EXECUTOR_CTX_SIZE,
        gpu_layers=EXECUTOR_GPU_LAYERS,
        llama_bin=llama_bin,
    )
    if proc is None:
        raise RuntimeError("실행기 모델 시작 실패 — 모델 파일을 확인하세요")

    ready = await wait_until_ready("executor", EXECUTOR_MODEL_URL)
    if not ready:
        raise RuntimeError("실행기 모델 로딩 타임아웃 — 서버를 시작할 수 없습니다")


async def start_light_and_wait(
    light_model: str,
    llama_bin: str = "llama-server",
) -> None:
    """경량(0.8B) 프로세스를 시작하고 준비될 때까지 대기한다."""
    proc = start_model(
        name="light",
        model_path=light_model,
        base_url=LIGHT_MODEL_URL,
        ctx_size=LIGHT_CTX_SIZE,
        gpu_layers=LIGHT_GPU_LAYERS,
        llama_bin=llama_bin,
    )
    if proc is None:
        raise RuntimeError("경량 모델 시작 실패 — 모델 파일을 확인하세요")
    ready = await wait_until_ready("light", LIGHT_MODEL_URL)
    if not ready:
        raise RuntimeError("경량 모델 로딩 타임아웃")


async def start_all_models(
    executor_model: str,
    light_model: str,
    llama_bin: str = "llama-server",
) -> None:
    """모든 모델을 병렬로 시작한다."""
    await asyncio.gather(
        start_executor_and_wait(executor_model, llama_bin),
        start_light_and_wait(light_model, llama_bin),
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
