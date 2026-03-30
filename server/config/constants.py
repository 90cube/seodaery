"""서버 전역 상수 정의. 하드코딩 금지 — 모든 설정값은 여기서 관리."""

import os

# --- llama.cpp 서버 엔드포인트 ---
ROUTER_MODEL_URL = os.getenv("ROUTER_MODEL_URL", "http://localhost:8081")
EXECUTOR_MODEL_URL = os.getenv("EXECUTOR_MODEL_URL", "http://localhost:8082")
LLAMA_COMPLETION_PATH = "/v1/chat/completions"

# --- 모델 식별자 ---
ROUTER_MODEL_NAME = os.getenv("ROUTER_MODEL_NAME", "qwen3.5-0.8b")
EXECUTOR_MODEL_NAME = os.getenv("EXECUTOR_MODEL_NAME", "qwen3.5-9b")

# --- VRAM 할당 (4070 Ti Super 16GB 기준) ---
ROUTER_GPU_LAYERS = int(os.getenv("ROUTER_GPU_LAYERS", "99"))
EXECUTOR_GPU_LAYERS = int(os.getenv("EXECUTOR_GPU_LAYERS", "99"))
ROUTER_CTX_SIZE = int(os.getenv("ROUTER_CTX_SIZE", "2048"))
EXECUTOR_CTX_SIZE = int(os.getenv("EXECUTOR_CTX_SIZE", "8192"))

# --- FastAPI ---
API_HOST = os.getenv("API_HOST", "127.0.0.1")
API_PORT = int(os.getenv("API_PORT", "8000"))

# --- 모델 파일 경로 ---
MODELS_DIR = os.getenv("MODELS_DIR", "models")
ROUTER_MODEL_FILE = os.getenv("ROUTER_MODEL_FILE", "Qwen3.5-0.8B-UD-Q8_K_XL.gguf")
EXECUTOR_MODEL_FILE = os.getenv("EXECUTOR_MODEL_FILE", "Qwen3.5-9B-Q8_0.gguf")

# --- llama-server 바이너리 ---
LLAMA_BIN = os.getenv("LLAMA_BIN", "llama-server")

# --- 라우터 설정 ---
ROUTER_TIMEOUT_SEC = float(os.getenv("ROUTER_TIMEOUT_SEC", "30.0"))
EXECUTOR_TIMEOUT_SEC = float(os.getenv("EXECUTOR_TIMEOUT_SEC", "120.0"))
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
