"""llama-server /slots API를 래핑하여 유저별 KV cache를 관리한다."""

import logging
import os

import httpx

from server.config.constants import EXECUTOR_MODEL_URL, KV_CACHE_DIR

logger = logging.getLogger(__name__)

_TIMEOUT = httpx.Timeout(30.0, connect=10.0)


def get_kv_path(user_id: str) -> str:
    """유저별 KV 저장 경로를 반환한다."""
    return os.path.join(KV_CACHE_DIR, user_id)


async def save_kv_slot(
    base_url: str,
    slot_id: int,
    save_path: str,
) -> bool:
    """llama-server의 KV cache를 디스크에 저장한다."""
    url = f"{base_url}/slots/{slot_id}?action=save"
    payload = {"filename": save_path}
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
        logger.info("KV cache saved: slot=%d path=%s", slot_id, save_path)
        return True
    except httpx.HTTPStatusError as exc:
        logger.error(
            "KV save HTTP error: slot=%d status=%d body=%s",
            slot_id,
            exc.response.status_code,
            exc.response.text,
        )
    except httpx.RequestError as exc:
        logger.error("KV save request error: slot=%d %s", slot_id, exc)
    return False


async def restore_kv_slot(
    base_url: str,
    slot_id: int,
    save_path: str,
) -> bool:
    """디스크에서 KV cache를 복원한다."""
    url = f"{base_url}/slots/{slot_id}?action=restore"
    payload = {"filename": save_path}
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
        logger.info("KV cache restored: slot=%d path=%s", slot_id, save_path)
        return True
    except httpx.HTTPStatusError as exc:
        logger.error(
            "KV restore HTTP error: slot=%d status=%d body=%s",
            slot_id,
            exc.response.status_code,
            exc.response.text,
        )
    except httpx.RequestError as exc:
        logger.error("KV restore request error: slot=%d %s", slot_id, exc)
    return False


async def erase_kv_slot(base_url: str, slot_id: int) -> bool:
    """KV cache 슬롯을 초기화한다."""
    url = f"{base_url}/slots/{slot_id}?action=erase"
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(url)
            resp.raise_for_status()
        logger.info("KV cache erased: slot=%d", slot_id)
        return True
    except httpx.HTTPStatusError as exc:
        logger.error(
            "KV erase HTTP error: slot=%d status=%d body=%s",
            slot_id,
            exc.response.status_code,
            exc.response.text,
        )
    except httpx.RequestError as exc:
        logger.error("KV erase request error: slot=%d %s", slot_id, exc)
    return False
