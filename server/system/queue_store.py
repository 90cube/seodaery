"""인메모리 요청 큐 및 결과 저장소. FIFO + 중복 방지 + 상태 알림."""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from collections import OrderedDict

_request_queue: asyncio.Queue | None = None
_results: OrderedDict[str, dict] = OrderedDict()
_subscribers: list[asyncio.Queue] = []
_pending_hashes: set[str] = set()
_processing_start: dict[str, float] = {}

RESULTS_MAX = 500


def _get_queue() -> asyncio.Queue:
    global _request_queue
    if _request_queue is None:
        _request_queue = asyncio.Queue()
    return _request_queue


def _make_dedup_key(user_id: str, message: str) -> str:
    """중복 방지용 해시 키를 생성한다."""
    raw = f"{user_id}:{message}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


async def enqueue_request(
    request_id: str, message: str, user_id: str = "anonymous"
) -> int | None:
    """요청을 큐에 추가한다. 중복이면 None 반환."""
    dedup_key = _make_dedup_key(user_id, message)
    if dedup_key in _pending_hashes:
        return None

    _pending_hashes.add(dedup_key)
    q = _get_queue()
    await q.put({
        "request_id": request_id,
        "message": message,
        "user_id": user_id,
        "dedup_key": dedup_key,
    })
    length = q.qsize()
    await _broadcast({
        "request_id": request_id,
        "event": "queued",
        "pending_count": length,
        "message": f"대기 {length}명",
    })
    return length


async def dequeue_request() -> dict | None:
    """큐에서 다음 요청을 꺼낸다. 비어 있으면 최대 5초 대기."""
    q = _get_queue()
    try:
        item = await asyncio.wait_for(q.get(), timeout=5.0)
    except asyncio.TimeoutError:
        return None

    _processing_start[item["request_id"]] = time.time()
    await _broadcast({
        "request_id": item["request_id"],
        "event": "processing",
        "message": "처리 시작",
    })
    return item


async def store_result(request_id: str, result: dict) -> None:
    """처리 결과를 저장하고 중복 해시를 제거한다."""
    _results[request_id] = result
    if len(_results) > RESULTS_MAX:
        _results.popitem(last=False)

    dedup_key = result.get("_dedup_key")
    if dedup_key:
        _pending_hashes.discard(dedup_key)
    _processing_start.pop(request_id, None)

    await _broadcast({
        "request_id": request_id,
        "event": "completed",
        "message": "처리 완료",
    })


def mark_dedup_done(dedup_key: str) -> None:
    """중복 해시를 수동으로 제거한다."""
    _pending_hashes.discard(dedup_key)


def get_result(request_id: str) -> dict | None:
    """저장된 결과를 조회한다."""
    return _results.get(request_id)


def get_queue_length() -> int:
    """현재 대기열 길이를 반환한다."""
    return _get_queue().qsize()


def subscribe() -> asyncio.Queue:
    """WebSocket 구독용 큐를 생성하여 반환한다."""
    q: asyncio.Queue = asyncio.Queue()
    _subscribers.append(q)
    return q


def unsubscribe(q: asyncio.Queue) -> None:
    """구독을 해제한다."""
    if q in _subscribers:
        _subscribers.remove(q)


async def _broadcast(data: dict) -> None:
    """모든 구독자에게 메시지를 전송한다."""
    msg = json.dumps(data, ensure_ascii=False)
    for q in _subscribers:
        try:
            q.put_nowait(msg)
        except asyncio.QueueFull:
            pass
