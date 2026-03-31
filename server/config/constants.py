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

# --- 서대리 페르소나 ---
PERSONA_NAME = "서영락"
PERSONA_POSITION = "대리"
PERSONA_PERSONALITY = (
    "센스있는 쾌남형. 존댓말을 사용하지만 딱딱하지 않고 편안한 톤. "
    "데이터베이스와 일정관리가 전문 분야."
)

PERSONA_SYSTEM_PROMPT = (
    f"당신의 이름은 {PERSONA_NAME}이고, 직급은 {PERSONA_POSITION}입니다. "
    f"{PERSONA_PERSONALITY}\n\n"
    "대화 시 규칙:\n"
    "1. 항상 한국어로 답변하세요.\n"
    "2. 내부 추론(Chain of Thought)은 숨기고 최종 답변만 출력하세요.\n"
    "3. 사용자의 이전 기억이 제공되면 자연스럽게 활용하세요.\n"
    "4. 센스있고 쾌활하게, 하지만 전문적으로 답변하세요."
)

# --- 유저 등록 ---
REGISTRATION_PROMPT = (
    "처음 뵙겠습니다! 저는 서대리 서영락입니다. "
    "원활한 소통을 위해 성함, 직급, 직무를 알려주시겠어요?"
)

REGISTRATION_VALIDATION_PROMPT = (
    "Extract user info from the text. Reply in JSON format ONLY.\n"
    "Required fields: name, position, role\n"
    "If any field is missing, set it to null.\n"
    'Example: {"name": "홍길동", "position": "과장", "role": "개발"}\n'
    "Output ONLY the JSON, nothing else."
)

# --- 기억 추출 ---
MEMORY_EXTRACTION_PROMPT = (
    "Extract key facts from this conversation as knowledge triples.\n"
    "Output as JSON array of objects with: subject, predicate, object\n"
    "Focus on: user preferences, important facts, decisions, requests.\n"
    "Ignore: greetings, filler, small talk.\n"
    '[{"subject":"사용자","predicate":"선호하는 언어","object":"Python"}]\n'
    "Output ONLY the JSON array."
)

# --- KV cache ---
KV_CACHE_DIR = os.getenv("KV_CACHE_DIR", "kv_cache")
KV_SLOT_ID = int(os.getenv("KV_SLOT_ID", "0"))

# --- DB ---
DB_DIR = os.getenv("DB_DIR", "db")

# --- 기억 검색 ---
MEMORY_SEARCH_PROMPT = (
    "Given the user message and available memory triples, "
    "select the most relevant triples for the response.\n"
    "Output the indices as JSON array: [0, 2, 5]\n"
    "If none are relevant, output: []\n"
    "Output ONLY the JSON array."
)
