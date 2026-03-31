"""파일 감시. watchdog으로 폴더 변경 감지.

에셋 폴더의 파일 생성·삭제를 실시간으로 감지하여 콜백을 호출한다.
watchdog 미설치 시 실시간 감시만 비활성화되며, 수동 스캔은 동작한다.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable

logger = logging.getLogger(__name__)

_watcher_available = False

try:
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer

    _watcher_available = True
except ImportError:
    FileSystemEventHandler = object  # type: ignore[assignment,misc]
    Observer = None  # type: ignore[assignment,misc]
    logger.warning("watchdog 미설치 (실시간 파일 감시 비활성)")

DEFAULT_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".txt"}

_on_created_cb: Callable[[str], None] | None = None
_on_deleted_cb: Callable[[str], None] | None = None
_observer = None


class _Handler(FileSystemEventHandler):
    """파일 생성·삭제 이벤트를 콜백으로 전달한다."""

    def on_created(self, event) -> None:  # noqa: ANN001
        if not event.is_directory and _on_created_cb:
            _on_created_cb(event.src_path)

    def on_deleted(self, event) -> None:  # noqa: ANN001
        if not event.is_directory and _on_deleted_cb:
            _on_deleted_cb(event.src_path)


def start_watching(
    folder: str,
    on_created: Callable[[str], None] | None = None,
    on_deleted: Callable[[str], None] | None = None,
) -> None:
    """폴더 감시를 시작한다. watchdog 미설치 시 경고만 출력한다."""
    global _on_created_cb, _on_deleted_cb, _observer

    if not _watcher_available:
        logger.warning("watchdog 미설치 — 실시간 감시 건너뜀")
        return

    target = Path(folder)
    if not target.is_dir():
        logger.error("감시 대상 폴더 없음: %s", folder)
        return

    _on_created_cb = on_created
    _on_deleted_cb = on_deleted
    _observer = Observer()
    _observer.schedule(_Handler(), str(target), recursive=True)
    _observer.start()
    logger.info("폴더 감시 시작: %s", folder)


def stop_watching() -> None:
    """폴더 감시를 중지한다."""
    global _observer
    if _observer is not None:
        _observer.stop()
        _observer.join()
        _observer = None
        logger.info("폴더 감시 중지")


def scan_folder(
    folder: str,
    extensions: set[str] | None = None,
) -> list[str]:
    """폴더 전체를 스캔하여 파일 경로 목록을 반환한다.

    Args:
        folder: 스캔 대상 폴더 경로.
        extensions: 허용 확장자 집합. None이면 기본 확장자 사용.

    Returns:
        매칭된 파일의 절대 경로 문자열 목록.
    """
    exts = extensions or DEFAULT_EXTENSIONS
    target = Path(folder)
    if not target.is_dir():
        logger.warning("스캔 대상 폴더 없음: %s", folder)
        return []

    results: list[str] = []
    for item in target.rglob("*"):
        if item.is_file() and item.suffix.lower() in exts:
            results.append(str(item))
    return sorted(results)


def is_watcher_available() -> bool:
    """watchdog 사용 가능 여부를 반환한다."""
    return _watcher_available
