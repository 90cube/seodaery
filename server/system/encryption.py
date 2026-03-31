"""Fernet 대칭키 암호화. 전송 구간만 암호화, DB는 평문."""
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_fernet = None
_available = False

KEY_PATH = os.getenv("ENCRYPTION_KEY_PATH", "shared.key")


def init_encryption():
    """shared.key에서 Fernet 키를 로드한다."""
    global _fernet, _available
    try:
        from cryptography.fernet import Fernet
        key_file = Path(KEY_PATH)
        if not key_file.exists():
            logger.warning(
                "shared.key 없음 — 암호화 비활성. "
                "tools/generate_key.py 실행 필요"
            )
            return
        key = key_file.read_bytes().strip()
        _fernet = Fernet(key)
        _available = True
        logger.info("Fernet 암호화 활성화")
    except ImportError:
        logger.warning("cryptography 미설치 — 암호화 비활성")
    except Exception as e:
        logger.error("암호화 초기화 실패: %s", e)


def is_available() -> bool:
    """암호화 사용 가능 여부를 반환한다."""
    return _available


def encrypt(data: bytes) -> bytes:
    """바이트 데이터를 암호화한다. 비활성 시 원본 반환."""
    if not _fernet:
        return data
    return _fernet.encrypt(data)


def decrypt(data: bytes) -> bytes:
    """바이트 데이터를 복호화한다. 비활성 시 원본 반환."""
    if not _fernet:
        return data
    return _fernet.decrypt(data)


def encrypt_str(text: str) -> str:
    """문자열을 암호화하여 base64 문자열로 반환."""
    return encrypt(text.encode()).decode()


def decrypt_str(token: str) -> str:
    """base64 토큰을 복호화하여 문자열로 반환."""
    return decrypt(token.encode()).decode()
