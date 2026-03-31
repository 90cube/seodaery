"""대시보드 API 클라이언트. 서버와 HTTP 통신 담당."""
import httpx

DEFAULT_TIMEOUT = 5.0


class DashboardClient:
    """서대리 서버 관리 API 동기 클라이언트."""

    def __init__(self, base_url: str):
        """클라이언트 초기화.

        Args:
            base_url: 서버 기본 URL (예: http://localhost:8000)
        """
        self._url = base_url.rstrip("/")
        self._timeout = DEFAULT_TIMEOUT

    def _get(self, path: str, params: dict | None = None) -> dict:
        """GET 요청 공통 처리."""
        resp = httpx.get(
            f"{self._url}{path}",
            params=params,
            timeout=self._timeout,
        )
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, json_body: dict | None = None) -> dict:
        """POST 요청 공통 처리."""
        resp = httpx.post(
            f"{self._url}{path}",
            json=json_body,
            timeout=self._timeout,
        )
        resp.raise_for_status()
        return resp.json()

    def get_queue_status(self) -> dict:
        """대기열 상태 조회."""
        return self._get("/api/admin/status")

    def get_admin_status(self) -> dict:
        """서버 전체 상태 조회. GET /api/admin/status"""
        return self._get("/api/admin/status")

    def get_admin_logs(self, limit: int = 100) -> dict:
        """최근 로그 조회. GET /api/admin/logs"""
        return self._get("/api/admin/logs", params={"limit": limit})

    def get_admin_clients(self) -> dict:
        """접속 중인 클라이언트 목록. GET /api/admin/clients"""
        return self._get("/api/admin/clients")

    def get_admin_gpu(self) -> dict:
        """GPU/모델 상태 조회. GET /api/admin/gpu"""
        return self._get("/api/admin/gpu")

    def get_admin_tools(self) -> dict:
        """등록된 도구 목록 조회. GET /api/admin/tools"""
        return self._get("/api/admin/tools")

    def toggle_tool(self, tool_id: str, enabled: bool) -> dict:
        """도구 활성화/비활성화 토글. POST /api/admin/tools/{id}/toggle"""
        return self._post(
            f"/api/admin/tools/{tool_id}/toggle",
            json_body={"enabled": enabled},
        )

    def get_schedules(self) -> dict:
        """스케줄 목록 조회. GET /api/schedule"""
        return self._get("/api/schedule")
