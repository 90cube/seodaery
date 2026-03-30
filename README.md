# 듀얼 모델 LLM 로컬 호스팅

0.8B 라우터 + 9B 멀티모달 실행기를 하나의 GPU(RTX 4070 Ti Super 16GB)에서 운용하는 로컬 추론 서버.
Docker, Linux, WSL 불필요 — Windows 네이티브 실행.

## 아키텍처

```
사용자 입력
    │
    ▼
FastAPI /api/chat (:8000)
    │
    ▼
인메모리 큐 (대기열)
    │
    ▼
0.8B 라우터 (:8081) ─→ 의도 분류
    │
    ├─ simple → 0.8B가 직접 응답
    │
    └─ complex → 9B 실행기 (:8082) → 응답
```

## 사전 준비

| 항목 | 요구사항 |
|------|----------|
| OS | Windows 10/11 |
| GPU | NVIDIA RTX 4070 Ti Super (VRAM 16GB) |
| CUDA | CUDA Toolkit 12.x + 최신 드라이버 |
| Python | 3.11+ |
| llama.cpp | llama-server 바이너리 (아래 설치 참고) |

### VRAM 예산

```
0.8B Q8          ≈  1.0 GB
9B   Q4_K_M (VL) ≈  5.5-6 GB
KV cache         ≈  1-2 GB
────────────────────────
합계             ≈  7.5-9 GB (여유 약 7-8GB)
```

## 프로젝트 구조

```
├── server/                       # 서버 (독립 실행)
│   ├── main.py                   # 진입점
│   ├── config/constants.py       # 전역 상수
│   ├── model/schemas.py          # 데이터 모델
│   ├── system/
│   │   ├── llama_client.py       # llama.cpp HTTP 래퍼
│   │   ├── queue_store.py        # 인메모리 큐 + 결과 저장
│   │   └── process_manager.py    # llama-server 프로세스 관리
│   ├── domain/
│   │   ├── intent_router.py      # 의도 분류 + 모델 실행
│   │   └── queue_processor.py    # 큐 워커
│   ├── api/
│   │   ├── chat.py               # REST 엔드포인트
│   │   └── websocket.py          # WebSocket 큐 상태 푸시
│   ├── models/                   # GGUF 모델 파일 (직접 배치)
│   └── requirements.txt
│
├── client/                       # 클라이언트 (서버와 코드 의존성 없음)
│   ├── main.py                   # CLI 진입점
│   ├── chat_client.py            # HTTP API 클라이언트
│   ├── ws_listener.py            # WebSocket 리스너
│   └── requirements.txt
```

## 설치 및 실행

### 1단계: llama.cpp 설치

GitHub Releases에서 Windows용 CUDA 빌드를 다운로드한다.

```powershell
# 예시: llama-b5000-bin-win-cuda-cu12.x-x64.zip 다운로드 후 압축 해제
# llama-server.exe 경로를 PATH에 추가하거나, 환경 변수 LLAMA_BIN에 설정
set LLAMA_BIN=C:\llama.cpp\llama-server.exe
```

### 2단계: 모델 파일 준비

```powershell
mkdir server\models
```

GGUF 포맷 모델을 `server/models/`에 배치한다.

| 용도 | 파일명 | 추천 모델 |
|------|--------|-----------|
| 라우터 (0.8B) | `router-0.8b.gguf` | Qwen2.5-0.5B, SmolLM2-360M |
| 실행기 (9B) | `qwen3.5-vl-9b.gguf` | Qwen3.5-VL-9B-Q4_K_M |

파일명이 다르면 환경 변수로 지정:

```powershell
set ROUTER_MODEL_FILE=my-router.gguf
set EXECUTOR_MODEL_FILE=my-executor.gguf
```

### 3단계: 서버 실행

```powershell
cd server
pip install -r requirements.txt
python -m server.main
```

서버가 시작되면 자동으로:
1. llama-server 프로세스 2개 기동 (포트 8081, 8082)
2. FastAPI 서버 시작 (포트 8000)
3. 큐 워커 백그라운드 실행

### 4단계: 클라이언트 실행 (별도 터미널)

```powershell
cd client
pip install -r requirements.txt
python main.py
```

다른 서버에 연결할 경우:

```powershell
python main.py http://192.168.1.100:8000
```

## API 명세

### REST

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/api/chat` | 채팅 요청 등록 |
| GET | `/api/chat/{request_id}` | 결과 폴링 |
| GET | `/api/queue/status` | 대기열 상태 |

```powershell
# 요청 등록
curl -X POST http://localhost:8000/api/chat -H "Content-Type: application/json" -d "{\"message\": \"hello\"}"

# 결과 폴링
curl http://localhost:8000/api/chat/a1b2c3d4e5f6
```

### WebSocket

`ws://localhost:8000/ws/queue` — 큐 상태 변경 시 자동 푸시.

## 환경 변수

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `LLAMA_BIN` | `llama-server` | llama-server 바이너리 경로 |
| `MODELS_DIR` | `models` | 모델 파일 디렉터리 |
| `ROUTER_MODEL_FILE` | `router-0.8b.gguf` | 라우터 모델 파일명 |
| `EXECUTOR_MODEL_FILE` | `qwen3.5-vl-9b.gguf` | 실행기 모델 파일명 |
| `ROUTER_MODEL_URL` | `http://localhost:8081` | 0.8B 서버 주소 |
| `EXECUTOR_MODEL_URL` | `http://localhost:8082` | 14B 서버 주소 |
| `API_HOST` | `127.0.0.1` | FastAPI 바인드 주소 |
| `API_PORT` | `8000` | FastAPI 포트 |
| `ROUTER_CTX_SIZE` | `2048` | 0.8B 컨텍스트 길이 |
| `EXECUTOR_CTX_SIZE` | `8192` | 9B 컨텍스트 길이 |

## 문제 해결

- **llama-server 실행 안됨** → `LLAMA_BIN` 경로 확인, CUDA 드라이버 설치 확인
- **OOM** → 환경 변수 `ROUTER_CTX_SIZE`, `EXECUTOR_CTX_SIZE` 축소
- **모델 로딩 느림** → 첫 요청 전 20~40초 대기 필요 (9B 모델)
- **타임아웃** → 환경 변수 `EXECUTOR_TIMEOUT_SEC` 조정
