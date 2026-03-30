"""인메모리 요청 큐 및 결과 저장소. Redis 대체 — 외부 의존성 없음."""

from __future__ import annotations

import asyncio
import json
from collections import OrderedDict

_request_queue: asyncio.Queue | None = None
_results: OrderedDict[str, dict] = OrderedDict()
_subscribers: list[asyncio.Queue] = []

RESULTS_MAX = 500


def _get_queue() -> asyncio.Queue:
    global _request_queue
    if _request_queue is None:
        _request_queue = asyncio.Queue()
    return _request_queue


async def enqueue_request(request_id: str, message: str) -> int:
    """요청을 큐에 추가하고 현재 대기열 길이를 반환한다."""
    q = _get_queue()
    await q.put({"request_id": request_id, "message": message})
    length = q.qsize()
    await _broadcast({"request_id": request_id, "pending_count": length})
    return length


async def dequeue_request() -> dict | None:
    """큐에서 다음 요청을 꺼낸다. 비어 있으면 최대 5초 대기."""
    q = _get_queue()
    try:
        return await asyncio.wait_for(q.get(), timeout=5.0)
    except asyncio.TimeoutError:
        return None


async def store_result(request_id: str, result: dict) -> None:
    """처리 결과를 저장한다."""
    _results[request_id] = result
    if len(_results) > RESULTS_MAX:
        _results.popitem(last=False)
    await _broadcast({"request_id": request_id, "status": "completed"})


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
    msg = json.dumps(data)
    for q in _subscribers:
        try:
            q.put_nowait(msg)
        except asyncio.QueueFull:
            pass
