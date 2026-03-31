"""암호화 미들웨어. 요청 복호화 + 응답 암호화."""
import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from server.system.encryption import is_available, decrypt, encrypt

logger = logging.getLogger(__name__)


class EncryptionMiddleware(BaseHTTPMiddleware):
    """Fernet 암호화 미들웨어.

    클라이언트가 X-Encrypted: true 헤더를 보내면:
    - 요청 body를 복호화
    - 응답 body를 암호화하고 X-Encrypted: true 헤더 추가

    암호화 비활성 또는 헤더 없으면 평문 통과.
    """

    async def dispatch(self, request: Request, call_next):
        """요청/응답 암호화 처리."""
        if not is_available():
            return await call_next(request)

        encrypted = (
            request.headers.get("X-Encrypted", "").lower() == "true"
        )

        if encrypted:
            body = await request.body()
            try:
                decrypted = decrypt(body)
                request._body = decrypted
            except Exception as e:
                logger.warning("요청 복호화 실패: %s", e)
                return Response(
                    content="Decryption failed",
                    status_code=400,
                )

        response = await call_next(request)

        if encrypted and response.status_code == 200:
            body = b""
            async for chunk in response.body_iterator:
                if isinstance(chunk, bytes):
                    body += chunk
                else:
                    body += chunk.encode()
            encrypted_body = encrypt(body)
            return Response(
                content=encrypted_body,
                status_code=response.status_code,
                headers={
                    **dict(response.headers),
                    "X-Encrypted": "true",
                },
                media_type=response.media_type,
            )

        return response
