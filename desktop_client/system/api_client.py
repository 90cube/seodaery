"""서버 통신 클라이언트. urllib 기반으로 외부 의존성 없이 동작한다."""
import json
import logging
import urllib.request
import urllib.error

logger = logging.getLogger(__name__)

_TIMEOUT = 10


class ApiClient:
    """서대리 서버와 HTTP 통신을 수행한다."""

    def __init__(self, base_url, user_id):
        self._url = base_url.rstrip("/")
        self._user_id = user_id

    def _get(self, path):
        """GET 요청을 보내고 JSON 응답을 반환한다."""
        url = f"{self._url}{path}"
        try:
            req = urllib.request.Request(url)
            req.add_header("X-User-Id", self._user_id)
            with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, OSError) as exc:
            logger.warning("GET %s 실패: %s", url, exc)
            return None

    def _post(self, path, body):
        """POST 요청을 보내고 JSON 응답을 반환한다."""
        url = f"{self._url}{path}"
        data = json.dumps(body).encode("utf-8")
        try:
            req = urllib.request.Request(url, data=data, method="POST")
            req.add_header("Content-Type", "application/json")
            req.add_header("X-User-Id", self._user_id)
            with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, OSError) as exc:
            logger.warning("POST %s 실패: %s", url, exc)
            return None

    def _get_raw(self, path):
        """GET 요청을 보내고 원시 바이트를 반환한다."""
        url = f"{self._url}{path}"
        try:
            req = urllib.request.Request(url)
            req.add_header("X-User-Id", self._user_id)
            with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
                return resp.read()
        except (urllib.error.URLError, OSError) as exc:
            logger.warning("GET(raw) %s 실패: %s", url, exc)
            return None

    def send_message(self, message):
        """채팅 메시지를 서버에 전송한다."""
        return self._post("/api/chat", {"message": message})

    def get_result(self, request_id):
        """비동기 요청의 결과를 조회한다."""
        return self._get(f"/api/chat/{request_id}")

    def get_queue_status(self):
        """대기열 상태를 조회한다."""
        return self._get("/api/queue")

    def get_schedules(self):
        """사용자의 일정 목록을 조회한다."""
        return self._get("/api/schedules")

    def create_schedule(self, data):
        """새 일정을 등록한다."""
        return self._post("/api/schedules", data)

    def get_files(self):
        """다운로드 가능한 파일 목록을 조회한다."""
        return self._get("/api/files")

    def download_file(self, file_id):
        """파일을 다운로드하여 바이트로 반환한다."""
        return self._get_raw(f"/api/files/{file_id}/download")

    def end_session(self):
        """세션을 종료한다."""
        return self._post("/api/session/end", {})
