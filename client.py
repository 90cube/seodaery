"""
서대리 채팅 클라이언트 (단일 파일, 외부 의존성 없음)
사용법: python client.py [서버주소]
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request
import uuid

DEFAULT_SERVER = "http://localhost:8000"
POLL_INTERVAL = 0.5
PROFILE_FILE = ".seodaery_profile"


def _headers(user_id: str) -> dict:
    return {"Content-Type": "application/json", "X-User-Id": user_id}


def _api_get(url: str, user_id: str, timeout: int = 5) -> dict | None:
    req = urllib.request.Request(url, headers=_headers(user_id))
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError:
        return None
    except urllib.error.URLError:
        return None


def _api_post(url: str, body: dict, user_id: str, timeout: int = 10) -> dict:
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=_headers(user_id))
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def load_profile(server: str) -> dict:
    """로컬 캐시 → 서버 조회 → 등록 폼 순서로 프로필을 확보한다."""
    # 1. 로컬 캐시
    if os.path.exists(PROFILE_FILE):
        with open(PROFILE_FILE, "r", encoding="utf-8") as f:
            profile = json.load(f)
        if profile.get("name"):
            return profile

    # user_id 확보
    user_id = ""
    if os.path.exists(PROFILE_FILE):
        with open(PROFILE_FILE, "r", encoding="utf-8") as f:
            user_id = json.load(f).get("user_id", "")
    if not user_id and os.path.exists(".seodaery_user_id"):
        with open(".seodaery_user_id", "r") as f:
            user_id = f.read().strip()
    if not user_id:
        user_id = uuid.uuid4().hex[:12]

    # 2. 서버 조회
    me = _api_get(f"{server}/api/user/me", user_id)
    if me and me.get("registered"):
        profile = {
            "user_id": user_id,
            "name": me.get("name", ""),
            "position": me.get("position", ""),
            "role": me.get("role", ""),
        }
        _save_profile(profile)
        return profile

    # 3. 등록 폼
    print("\n  === 서대리 첫 실행 등록 ===")
    name = input("  이름: ").strip()
    if not name:
        name = "익명"
    position = input("  직급 (생략 가능): ").strip()
    role = input("  직무 (생략 가능): ").strip()

    try:
        _api_post(
            f"{server}/api/register",
            {"name": name, "position": position, "role": role},
            user_id,
        )
    except Exception as e:
        print(f"  [경고] 서버 등록 실패: {e} (로컬만 저장)")

    profile = {"user_id": user_id, "name": name, "position": position, "role": role}
    _save_profile(profile)
    return profile


def _save_profile(profile: dict) -> None:
    with open(PROFILE_FILE, "w", encoding="utf-8") as f:
        json.dump(profile, f, ensure_ascii=False, indent=2)


def wait_for_result(server: str, request_id: str) -> dict:
    spinner = ["|", "/", "-", "\\"]
    idx = 0
    while True:
        result = _api_get(f"{server}/api/chat/{request_id}", "")
        if result and result.get("status") in ("completed", "error"):
            print("\r" + " " * 40 + "\r", end="")
            return result
        pending = result.get("pending_count", "?") if result else "?"
        print(f"\r  {spinner[idx]} 처리 중... (대기열: {pending}건)", end="", flush=True)
        idx = (idx + 1) % len(spinner)
        time.sleep(POLL_INTERVAL)


def main() -> None:
    server = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SERVER

    print("=" * 40)
    print("  서대리 채팅 클라이언트")
    print(f"  서버: {server}")
    print("=" * 40)

    # 프로필 확보 (캐시 → 서버 → 등록 폼)
    profile = load_profile(server)
    user_id = profile["user_id"]
    name = profile.get("name", "?")

    print(f"  유저: {name} ({user_id})")
    print("  종료: quit 또는 Ctrl+C")

    try:
        status = _api_get(f"{server}/api/queue/status", user_id)
        if status:
            print(f"  서버 연결 성공 (대기열: {status['pending_count']}건)\n")
        else:
            print("  [경고] 서버에 연결할 수 없습니다.\n")
    except Exception:
        print("  [경고] 서버에 연결할 수 없습니다.\n")

    try:
        while True:
            try:
                message = input(f"{name}> ").strip()
            except EOFError:
                break
            if message.lower() in ("quit", "exit", "q"):
                break
            if not message:
                continue
            try:
                queued = _api_post(f"{server}/api/chat", {"message": message}, user_id)
                if queued.get("duplicate"):
                    print("  [중복] 같은 요청이 처리 중입니다.\n")
                    continue
                request_id = queued["request_id"]
                print(f"  [전송] 대기열={queued.get('position', '?')}번째")
                result = wait_for_result(server, request_id)
                model = result.get("model_used", "?")
                content = result.get("content", "(응답 없음)")
                print(f"  [{model}] {content}\n")
            except urllib.error.URLError as e:
                print(f"  [오류] 서버 통신 실패: {e}\n")
    except KeyboardInterrupt:
        pass

    print("\n  세션 종료 중...")
    try:
        _api_post(f"{server}/api/session/end", {}, user_id, timeout=30)
    except Exception:
        pass
    print("  종료합니다.")


if __name__ == "__main__":
    main()
