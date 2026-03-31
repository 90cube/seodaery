"""인메모리 rate limiter. dict + timestamp 기반.

외부 의존성 없이 사용자별 요청 빈도를 제한한다.
"""

import time

_requests: dict[str, list[float]] = {}

DEFAULT_LIMIT = 30   # 윈도우당 최대 요청 수
DEFAULT_WINDOW = 60  # 윈도우 크기 (초)


def check_rate_limit(
    user_id: str,
    limit: int = DEFAULT_LIMIT,
    window: int = DEFAULT_WINDOW,
) -> tuple[bool, int]:
    """요청 허용 여부를 확인한다.

    Args:
        user_id: 사용자 식별자.
        limit: 윈도우 내 최대 허용 요청 수.
        window: 시간 윈도우(초).

    Returns:
        (allowed, remaining) 튜플. allowed가 False이면 차단.
    """
    now = time.time()

    if user_id not in _requests:
        _requests[user_id] = []

    # 윈도우 밖 항목 정리
    _requests[user_id] = [
        t for t in _requests[user_id] if now - t < window
    ]

    if len(_requests[user_id]) >= limit:
        return False, 0

    _requests[user_id].append(now)
    remaining = limit - len(_requests[user_id])
    return True, remaining


def get_usage(
    user_id: str, window: int = DEFAULT_WINDOW
) -> int:
    """현재 윈도우 내 사용자의 요청 수를 반환한다.

    Args:
        user_id: 사용자 식별자.
        window: 시간 윈도우(초).

    Returns:
        윈도우 내 요청 횟수.
    """
    now = time.time()
    entries = _requests.get(user_id, [])
    return sum(1 for t in entries if now - t < window)


def reset(user_id: str) -> None:
    """특정 사용자의 요청 기록을 초기화한다."""
    _requests.pop(user_id, None)


def reset_all() -> None:
    """전체 요청 기록을 초기화한다."""
    _requests.clear()
