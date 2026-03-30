"""WebSocket 엔드포인트. 큐 상태를 실시간 푸시한다."""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from server.config.constants import QUEUE_STATUS_CHANNEL
from server.system.redis_client import get_redis

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/queue")
async def queue_websocket(ws: WebSocket):
    """Redis Pub/Sub를 구독하여 큐 상태 변경을 클라이언트에 푸시한다."""
    await ws.accept()

    r = await get_redis()
    pubsub = r.pubsub()
    await pubsub.subscribe(QUEUE_STATUS_CHANNEL)

    try:
        while True:
            msg = await pubsub.get_message(
                ignore_subscribe_messages=True, timeout=1.0
            )
            if msg and msg["type"] == "message":
                await ws.send_text(msg["data"])
            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        pass
    finally:
        await pubsub.unsubscribe(QUEUE_STATUS_CHANNEL)
        await pubsub.aclose()
