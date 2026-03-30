# 듀얼 모델 LLM 로컬 호스팅

0.8B 라우터 + 14B 실행기를 하나의 GPU(RTX 4070 Ti Super 16GB)에서 운용하는 로컬 추론 서버.

## 아키텍처

```
사용자 입력
    │
    ▼
FastAPI /api/chat (:8000)
    │
    ▼
Redis Queue (대기열)
    │
    ▼
0.8B 라우터 (:8081) ─→ 의도 분류
    │
    ├─ simple → 0.8B가 직접 응답
    │
    └─ complex → 14B 실행기 (:8082) → 응답
```

## 사전 준비

| 항목 | 요구사항 |
|------|----------|
| OS | Linux (CUDA 지원) |
| GPU | NVIDIA RTX 4070 Ti Super (VRAM 16GB) |
| Docker | Docker Engine + NVIDIA Container Toolkit |
| Python | 3.11+ |

### VRAM 예산

```
0.8B Q8     ≈  1.0 GB
14B  Q4_K_M ≈  8.5 GB
KV cache    ≈  1-2 GB
────────────────────
합계        ≈ 10.5-11.5 GB (여유 약 4GB)
```

## 프로젝트 구조

```
├── server/                  # 서버 (독립 실행)
│   ├── main.py              # 진입점
│   ├── config/constants.py  # 전역 상수
│   ├── model/schemas.py     # 데이터 모델
│   ├── system/
│   │   ├── llama_client.py  # llama.cpp HTTP 래퍼
│   │   └── redis_client.py  # Redis 큐 조작
│   ├── domain/
│   │   ├── intent_router.py # 의도 분류 + 모델 실행
│   │   └── queue_processor.py # 큐 워커
│   ├── api/
│   │   ├── chat.py          # REST 엔드포인트
│   │   └── websocket.py     # WebSocket 큐 상태 푸시
│   ├── docker-compose.yml
│   └── requirements.txt
│
├── client/                  # 클라이언트 (서버와 코드 의존성 없음)
│   ├── main.py              # CLI 진입점
│   ├── chat_client.py       # HTTP API 클라이언트
│   ├── ws_listener.py       # WebSocket 리스너
│   └── requirements.txt
```

## 설치 및 실행

### 1단계: 모델 파일 준비

```bash
mkdir -p server/models
```

[Hugging Face](https://huggingface.co)에서 GGUF 포맷 모델을 다운로드하여 `server/models/`에 배치한다.

| 용도 | 파일명 | 추천 모델 |
|------|--------|-----------|
| 라우터 (0.8B) | `router-0.8b.gguf` | Qwen2.5-0.5B, SmolLM2-360M 등 |
| 실행기 (14B) | `executor-14b.gguf` | Qwen2.5-14B-Q4_K_M, Mistral-Nemo 등 |

모델명이 다르면 `docker-compose.yml`의 `--model` 경로를 수정한다.

### 2단계: 인프라 시작 (Docker)

```bash
cd server
docker compose up -d
```

컨테이너 3개가 올라온다:

| 서비스 | 포트 | 설명 |
|--------|------|------|
| redis | 6379 | 요청 큐, 결과 저장 |
| router-model | 8081 | 0.8B llama.cpp 서버 |
| executor-model | 8082 | 14B llama.cpp 서버 |

헬스 체크:

```bash
curl http://localhost:8081/health
curl http://localhost:8082/health
```

### 3단계: 서버 실행

```bash
cd server
pip install -r requirements.txt
python -m server.main
```

FastAPI가 `http://localhost:8000`에서 시작된다.

### 4단계: 클라이언트 실행 (별도 터미널)

```bash
cd client
pip install -r requirements.txt
python main.py
```

다른 서버에 연결할 경우:

```bash
python main.py http://192.168.1.100:8000
```

## API 명세

### REST

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/api/chat` | 채팅 요청 등록 |
| GET | `/api/chat/{request_id}` | 결과 폴링 |
| GET | `/api/queue/status` | 대기열 상태 |

```bash
# 요청 등록
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "안녕하세요"}'
# → {"request_id": "a1b2c3d4e5f6", "status": "queued", "position": 1}

# 결과 폴링
curl http://localhost:8000/api/chat/a1b2c3d4e5f6
# → {"request_id": "...", "content": "...", "model_used": "router-0.8b", "intent": "simple", "status": "completed"}
```

### WebSocket

`ws://localhost:8000/ws/queue`로 연결하면 큐 상태 변경 시 자동 푸시된다.

## 환경 변수

모든 설정은 환경 변수로 오버라이드 가능하다.

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `ROUTER_MODEL_URL` | `http://localhost:8081` | 0.8B 서버 주소 |
| `EXECUTOR_MODEL_URL` | `http://localhost:8082` | 14B 서버 주소 |
| `REDIS_HOST` | `localhost` | Redis 호스트 |
| `REDIS_PORT` | `6379` | Redis 포트 |
| `API_HOST` | `0.0.0.0` | FastAPI 바인드 주소 |
| `API_PORT` | `8000` | FastAPI 포트 |
| `ROUTER_CTX_SIZE` | `2048` | 0.8B 컨텍스트 길이 |
| `EXECUTOR_CTX_SIZE` | `4096` | 14B 컨텍스트 길이 |

## 문제 해결

- **`/health` 실패** → 모델 로딩 중. `docker compose logs -f`로 확인
- **OOM** → `docker-compose.yml`에서 `--ctx-size` 축소
- **Redis 연결 실패** → `docker compose up -d redis`
- **14B 타임아웃** → 환경 변수 `EXECUTOR_TIMEOUT_SEC` 조정
