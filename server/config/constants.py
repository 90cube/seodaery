"""서버 전역 상수 정의. 하드코딩 금지 — 모든 설정값은 여기서 관리."""

import os

# --- llama.cpp 서버 엔드포인트 ---
ROUTER_MODEL_URL = os.getenv("ROUTER_MODEL_URL", "http://localhost:8081")
EXECUTOR_MODEL_URL = os.getenv("EXECUTOR_MODEL_URL", "http://localhost:8082")
LLAMA_COMPLETION_PATH = "/v1/chat/completions"

# --- 모델 식별자 ---
ROUTER_MODEL_NAME = os.getenv("ROUTER_MODEL_NAME", "router-0.8b")
EXECUTOR_MODEL_NAME = os.getenv("EXECUTOR_MODEL_NAME", "executor-14b")

# --- VRAM 할당 (4070 Ti Super 16GB 기준) ---
ROUTER_GPU_LAYERS = int(os.getenv("ROUTER_GPU_LAYERS", "99"))
EXECUTOR_GPU_LAYERS = int(os.getenv("EXECUTOR_GPU_LAYERS", "99"))
ROUTER_CTX_SIZE = int(os.getenv("ROUTER_CTX_SIZE", "2048"))
EXECUTOR_CTX_SIZE = int(os.getenv("EXECUTOR_CTX_SIZE", "4096"))

# --- Redis ---
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
QUEUE_KEY = "chat:request_queue"
RESULT_KEY_PREFIX = "chat:result:"
QUEUE_STATUS_CHANNEL = "chat:queue_status"

# --- FastAPI ---
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))

# --- 라우터 설정 ---
ROUTER_TIMEOUT_SEC = 2.0
EXECUTOR_TIMEOUT_SEC = 120.0
ROUTER_MAX_TOKENS = 20
EXECUTOR_MAX_TOKENS = 2048

# --- 의도 분류 ---
INTENT_SIMPLE = "simple"
INTENT_COMPLEX = "complex"

INTENT_CLASSIFICATION_PROMPT = (
    "You are an intent classifier. "
    "Classify the user message as 'simple' or 'complex'.\n"
    "simple: greetings, yes/no questions, factual lookups, single-sentence answers.\n"
    "complex: reasoning, coding, multi-step tasks, creative writing, analysis.\n"
    "Reply with ONLY one word: simple or complex"
)
