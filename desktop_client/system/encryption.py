"""클라이언트 측 Fernet 암호화. cryptography 패키지 선택적 의존."""
import os
import logging

logger = logging.getLogger(__name__)

_fernet = None
KEY_PATH = os.path.join(os.path.dirname(__file__), "..", "shared.key")


def init():
    """공유 키 파일이 있으면 Fernet 인스턴스를 초기화한다."""
    global _fernet
    try:
        from cryptography.fernet import Fernet
    except ImportError:
        logger.info("cryptography 패키지 없음 — 암호화 비활성")
        return

    resolved = os.path.abspath(KEY_PATH)
    if os.path.exists(resolved):
        with open(resolved, "rb") as f:
            key = f.read().strip()
        _fernet = Fernet(key)
        logger.info("Fernet 암호화 초기화 완료")
    else:
        logger.info("키 파일 없음(%s) — 암호화 비활성", resolved)


def encrypt(data: bytes) -> bytes:
    """데이터를 암호화한다. 비활성 시 원본을 그대로 반환한다."""
    if _fernet is None:
        return data
    return _fernet.encrypt(data)


def decrypt(data: bytes) -> bytes:
    """데이터를 복호화한다. 비활성 시 원본을 그대로 반환한다."""
    if _fernet is None:
        return data
    try:
        return _fernet.decrypt(data)
    except Exception:
        logger.error("복호화 실패")
        return data


def is_available() -> bool:
    """암호화 기능이 사용 가능한지 반환한다."""
    return _fernet is not None
