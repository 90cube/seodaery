# 듀얼 모델 LLM 로컬 호스팅

0.8B 라우터 + Qwen3.5-VL-9B 멀티모달 실행기를 하나의 GPU에서 운용하는 로컬 추론 서버.
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
| Python | 3.13 |
| llama.cpp | llama-server 바이너리 |

### VRAM 예산

```
0.8B Q8          ≈  1.0 GB
9B   Q4_K_M (VL) ≈  5.7 GB
mmproj-F16       ≈  0.9 GB
KV cache         ≈  1-2 GB
────────────────────────
합계             ≈  8.6-9.6 GB (여유 약 6-7GB)
```

## 프로젝트 구조

```
├── setup.bat                     # 초기 설치 (venv + 폴더 + pip)
├── start_server.bat              # 서버 시작
├── client.py                     # 클라이언트 (단일 파일, 의존성 없음)
│
├── server/
│   ├── main.py                   # 진입점
│   ├── requirements.txt
│   ├── .venv/                    # (setup.bat이 생성)
│   ├── models/                   # (setup.bat이 생성, GGUF 배치)
│   ├── config/constants.py       # 전역 상수
│   ├── model/schemas.py          # 데이터 모델
│   ├── system/
│   │   ├── llama_client.py       # llama.cpp HTTP 래퍼
│   │   ├── queue_store.py        # 인메모리 큐 + 결과 저장
│   │   └── process_manager.py    # llama-server 프로세스 관리
│   ├── domain/
│   │   ├── intent_router.py      # 의도 분류 + 모델 실행
│   │   └── queue_processor.py    # 큐 워커
│   └── api/
│       ├── chat.py               # REST 엔드포인트
│       └── websocket.py          # WebSocket 큐 상태 푸시
```

## 설치 및 실행

### 1단계: llama.cpp 설치

GitHub Releases에서 Windows CUDA 빌드를 다운로드 후 압축 해제.

```powershell
set LLAMA_BIN=C:\llama.cpp\llama-server.exe
```

PATH에 추가하거나, 환경 변수 `LLAMA_BIN`에 전체 경로를 설정한다.

### 2단계: 모델 다운로드

| 파일 | 크기 | 배치 경로 |
|------|------|-----------|
| `Qwen3.5-9B-Q4_K_M.gguf` | 5.68 GB | `server\models\qwen3.5-vl-9b.gguf` |
| `mmproj-F16.gguf` | 918 MB | (비전 사용 시에만) |
| 라우터 0.8B GGUF | ~0.5-1 GB | `server\models\router-0.8b.gguf` |

파일명이 다르면 환경 변수 `ROUTER_MODEL_FILE`, `EXECUTOR_MODEL_FILE`로 지정.

### 3단계: 초기 설치

```powershell
setup.bat
```

자동으로 수행되는 작업:
- `server\models\` 폴더 생성
- Python 3.13 가상환경 생성 (`server\.venv\`)
- pip 패키지 설치

### 4단계: 서버 시작

```powershell
start_server.bat
```

### 5단계: 클라이언트 실행 (별도 터미널)

```powershell
python client.py
```

다른 PC에서 연결:

```powershell
python client.py http://192.168.1.100:8000
```

클라이언트는 Python 표준 라이브러리만 사용하므로 `pip install` 불필요.

## API 명세

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/api/chat` | 채팅 요청 등록 |
| GET | `/api/chat/{request_id}` | 결과 폴링 |
| GET | `/api/queue/status` | 대기열 상태 |
| WS | `/ws/queue` | 큐 상태 실시간 푸시 |

## 환경 변수

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `LLAMA_BIN` | `llama-server` | llama-server 바이너리 경로 |
| `MODELS_DIR` | `models` | 모델 파일 디렉터리 |
| `ROUTER_MODEL_FILE` | `router-0.8b.gguf` | 라우터 모델 파일명 |
| `EXECUTOR_MODEL_FILE` | `qwen3.5-vl-9b.gguf` | 실행기 모델 파일명 |
| `API_PORT` | `8000` | FastAPI 포트 |
| `ROUTER_CTX_SIZE` | `2048` | 0.8B 컨텍스트 길이 |
| `EXECUTOR_CTX_SIZE` | `8192` | 9B 컨텍스트 길이 |

## 문제 해결

- **llama-server 실행 안됨** → `LLAMA_BIN` 경로 확인, CUDA 드라이버 설치 확인
- **OOM** → 환경 변수 `ROUTER_CTX_SIZE`, `EXECUTOR_CTX_SIZE` 축소
- **모델 로딩 느림** → 첫 요청 전 20~40초 대기 필요
- **타임아웃** → 환경 변수 `EXECUTOR_TIMEOUT_SEC` 조정
