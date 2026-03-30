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

# --- 타임아웃 ---
ROUTER_TIMEOUT_SEC = float(os.getenv("ROUTER_TIMEOUT_SEC", "30.0"))
EXECUTOR_TIMEOUT_SEC = float(os.getenv("EXECUTOR_TIMEOUT_SEC", "120.0"))
ROUTER_MAX_TOKENS = 10
EXECUTOR_MAX_TOKENS = 2048

# --- 입력 타입 분류 ---
INPUT_TYPE_TEXT = "text"
INPUT_TYPE_IMAGE = "image"
INPUT_TYPE_WORKER = "worker"

INPUT_TYPE_CLASSIFICATION_PROMPT = (
    "Classify the input type. Reply with ONLY one word.\n\n"
    "text: plain text message, question, conversation\n"
    "image: contains image, photo, picture, or visual content\n"
    "worker: automated task, scheduled job, system command\n\n"
    "Output ONLY one word: text or image or worker"
)

# --- 9B 실행기 시스템 프롬프트 ---
EXECUTOR_SYSTEM_PROMPT = (
    "You are a helpful Korean-speaking assistant. "
    "You MUST use Zero-shot Chain of Thought reasoning.\n\n"
    "For every question:\n"
    "Step 1: Restate the core question in your own words.\n"
    "Step 2: Break it into sub-problems or key points.\n"
    "Step 3: Reason through each sub-problem one by one.\n"
    "Step 4: Synthesize into a clear, structured final answer.\n\n"
    "Always respond in Korean. Show your reasoning process explicitly."
)
