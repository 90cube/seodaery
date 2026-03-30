"""Redis 연결 및 큐 조작. 단일 책임: Redis I/O만."""

from __future__ import annotations

import json

import redis.asyncio as aioredis

from server.config.constants import (
    QUEUE_KEY,
    QUEUE_STATUS_CHANNEL,
    REDIS_DB,
    REDIS_HOST,
    REDIS_PORT,
    RESULT_KEY_PREFIX,
)

_pool: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    """싱글턴 Redis 연결을 반환한다."""
    global _pool
    if _pool is None:
        _pool = aioredis.Redis(
            host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True
        )
    return _pool


async def enqueue_request(request_id: str, message: str) -> int:
    """요청을 큐에 추가하고 현재 대기열 길이를 반환한다."""
    r = await get_redis()
    payload = json.dumps({"request_id": request_id, "message": message})
    length = await r.rpush(QUEUE_KEY, payload)
    await r.publish(
        QUEUE_STATUS_CHANNEL,
        json.dumps({"request_id": request_id, "pending_count": length}),
    )
    return length


async def dequeue_request() -> dict | None:
    """큐에서 다음 요청을 꺼낸다. 비어 있으면 최대 5초 대기."""
    r = await get_redis()
    result = await r.blpop(QUEUE_KEY, timeout=5)
    if result is None:
        return None
    _, payload = result
    return json.loads(payload)


async def store_result(request_id: str, result: dict, ttl: int = 300) -> None:
    """처리 결과를 Redis에 저장한다."""
    r = await get_redis()
    key = f"{RESULT_KEY_PREFIX}{request_id}"
    await r.set(key, json.dumps(result), ex=ttl)
    await r.publish(
        QUEUE_STATUS_CHANNEL,
        json.dumps({"request_id": request_id, "status": "completed"}),
    )


async def get_result(request_id: str) -> dict | None:
    """저장된 결과를 조회한다."""
    r = await get_redis()
    raw = await r.get(f"{RESULT_KEY_PREFIX}{request_id}")
    return json.loads(raw) if raw else None


async def get_queue_length() -> int:
    """현재 대기열 길이를 반환한다."""
    r = await get_redis()
    return await r.llen(QUEUE_KEY)


async def close() -> None:
    """Redis 연결을 종료한다."""
    global _pool
    if _pool is not None:
        await _pool.aclose()
        _pool = None
