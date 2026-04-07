"""n8n 연동 테스트 브리지. 모델 없이 API만 열어서 연결 확인용."""

import json
import socket
import sys
from datetime import datetime

import uvicorn
from fastapi import FastAPI, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# 0.0.0.0으로 바인딩해야 외부(n8n)에서 접근 가능
HOST = "0.0.0.0"
PORT = 8000

app = FastAPI(title="서대리 n8n Bridge", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_log: list[dict] = []


def _add_log(action: str, data: dict) -> None:
    entry = {"time": datetime.now().isoformat(), "action": action, **data}
    _log.append(entry)
    if len(_log) > 100:
        _log.pop(0)
    print(f"  [{entry['time'][11:19]}] {action}: {json.dumps(data, ensure_ascii=False)[:120]}")


# ── 연결 확인용 ──────────────────────────────────────────


@app.get("/")
async def root():
    """n8n에서 연결 확인용."""
    return {
        "service": "서대리 n8n Bridge",
        "status": "online",
        "time": datetime.now().isoformat(),
    }


@app.get("/api/n8n/ping")
async def ping():
    """가장 단순한 연결 테스트."""
    return {"pong": True, "time": datetime.now().isoformat()}


# ── 도구 직접 호출 (에코 모드) ────────────────────────────


@app.post("/api/n8n/tool")
async def tool(
    body: dict,
    x_n8n_action: str = Header(..., alias="X-N8N-Action"),
    x_user_id: str = Header(default="n8n"),
):
    """도구 호출 에코. 받은 그대로 돌려준다."""
    _add_log("tool", {"action": x_n8n_action, "params": body})
    return {
        "echo": True,
        "action": x_n8n_action,
        "params": body,
        "user_id": x_user_id,
        "message": f"도구 '{x_n8n_action}' 호출 수신 완료 (에코 모드)",
    }


# ── 채팅 (에코 모드) ─────────────────────────────────────


@app.post("/api/n8n/chat")
async def chat(
    body: dict,
    x_user_id: str = Header(default="n8n"),
):
    """채팅 에코. 받은 메시지를 그대로 돌려준다."""
    message = body.get("message", "")
    _add_log("chat", {"message": message, "user_id": x_user_id})
    return {
        "echo": True,
        "content": f"[에코] {message}",
        "model_used": "echo",
        "status": "completed",
    }


# ── 로그 확인 ─────────────────────────────────────────────


@app.get("/api/n8n/log")
async def get_log():
    """n8n에서 보낸 요청 기록을 확인한다."""
    return {"count": len(_log), "entries": _log[-20:]}


@app.get("/api/n8n/tools")
async def list_tools():
    return {"tools": ["create_schedule", "list_schedules"]}


# ── 시작 ──────────────────────────────────────────────────


def _get_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "알 수 없음"


if __name__ == "__main__":
    local_ip = _get_local_ip()
    print()
    print("  ========================================")
    print("  n8n Bridge 시작")
    print(f"  로컬:  http://localhost:{PORT}")
    print(f"  외부:  http://{local_ip}:{PORT}")
    print("  ========================================")
    print()
    print("  n8n에서 테스트:")
    print(f"    GET  http://{local_ip}:{PORT}/api/n8n/ping")
    print(f"    POST http://{local_ip}:{PORT}/api/n8n/chat")
    print(f"    POST http://{local_ip}:{PORT}/api/n8n/tool")
    print()
    print("  요청 기록 확인:")
    print(f"    GET  http://{local_ip}:{PORT}/api/n8n/log")
    print()
    print("  종료: Ctrl+C")
    print("  ─────────────────────────────────────────")
    print()

    uvicorn.run(app, host=HOST, port=PORT)
