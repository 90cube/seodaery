"""관리자 REST API 엔드포인트. 대시보드 전용."""
import subprocess
import time
from datetime import datetime, timezone

from fastapi import APIRouter

router = APIRouter(prefix="/api/admin", tags=["admin"])

_start_time = time.time()


@router.get("/status")
async def status() -> dict:
    """서버 가동 시간 및 대기열 상태 반환."""
    uptime_sec = int(time.time() - _start_time)
    return {
        "uptime_seconds": uptime_sec,
        "started_at": datetime.fromtimestamp(
            _start_time, tz=timezone.utc
        ).isoformat(),
        "queue": {
            "pending": 0,
            "processing": 0,
        },
    }


@router.get("/logs")
async def logs(limit: int = 100) -> dict:
    """최근 로그 항목 반환.

    Args:
        limit: 반환할 로그 최대 개수
    """
    # TODO: 실제 로그 저장소 연동
    return {"logs": [], "count": 0, "limit": limit}


@router.get("/clients")
async def clients() -> dict:
    """현재 접속 중인 클라이언트 목록 반환."""
    # TODO: session_manager 연동
    return {"clients": [], "count": 0}


@router.get("/gpu")
async def gpu() -> dict:
    """GPU 및 모델 정보 반환. nvidia-smi 사용 시도."""
    gpus = _get_nvidia_gpu_info()
    # TODO: 모델 레지스트리 연동
    return {"gpus": gpus, "models": []}


@router.get("/tools")
async def tools() -> dict:
    """등록된 도구 목록 반환."""
    # TODO: tool_registry 연동
    return {"tools": []}


@router.post("/tools/{tool_id}/toggle")
async def toggle_tool(tool_id: str, body: dict) -> dict:
    """도구 활성화/비활성화 토글.

    Args:
        tool_id: 대상 도구 식별자
        body: {"enabled": bool}
    """
    enabled = body.get("enabled", True)
    # TODO: tool_registry 연동
    return {
        "tool_id": tool_id,
        "enabled": enabled,
        "message": "변경 완료",
    }


def _get_nvidia_gpu_info() -> list:
    """nvidia-smi로 GPU 정보 조회. 실패 시 빈 리스트."""
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=index,name,memory.used,memory.total,temperature.gpu",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return []
        gpus = []
        for line in result.stdout.strip().split("\n"):
            if not line.strip():
                continue
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 5:
                gpus.append({
                    "id": parts[0],
                    "name": parts[1],
                    "vram_usage": f"{parts[2]}MB / {parts[3]}MB",
                    "temperature": f"{parts[4]}°C",
                })
        return gpus
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []
