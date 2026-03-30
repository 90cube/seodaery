"""데이터 모델 정의. 상태 정의만, 연산 금지."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum


class Intent(str, Enum):
    SIMPLE = "simple"
    COMPLEX = "complex"


class RequestStatus(str, Enum):
    QUEUED = "queued"
    ROUTING = "routing"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class ChatRequest:
    message: str
    request_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    created_at: float = field(default_factory=time.time)


@dataclass
class ChatResponse:
    request_id: str
    content: str
    model_used: str
    intent: str
    status: str = RequestStatus.COMPLETED.value


@dataclass
class QueueStatus:
    request_id: str
    position: int
    status: str
    pending_count: int
