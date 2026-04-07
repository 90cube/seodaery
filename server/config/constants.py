"""서버 전역 상수 정의. 하드코딩 금지 — 모든 설정값은 여기서 관리."""

import os

# --- llama.cpp 서버 엔드포인트 ---
EXECUTOR_MODEL_URL = os.getenv("EXECUTOR_MODEL_URL", "http://localhost:8082")
LIGHT_MODEL_URL = os.getenv("LIGHT_MODEL_URL", "http://localhost:8081")
LLAMA_COMPLETION_PATH = "/v1/chat/completions"

# --- 모델 식별자 ---
EXECUTOR_MODEL_NAME = os.getenv("EXECUTOR_MODEL_NAME", "qwen3.5-9b")
LIGHT_MODEL_NAME = os.getenv("LIGHT_MODEL_NAME", "qwen3.5-0.8b")

# --- VRAM 할당 (4070 Ti Super 16GB 기준) ---
EXECUTOR_GPU_LAYERS = int(os.getenv("EXECUTOR_GPU_LAYERS", "99"))
EXECUTOR_CTX_SIZE = int(os.getenv("EXECUTOR_CTX_SIZE", "8192"))
LIGHT_GPU_LAYERS = int(os.getenv("LIGHT_GPU_LAYERS", "99"))
LIGHT_CTX_SIZE = int(os.getenv("LIGHT_CTX_SIZE", "2048"))

# --- FastAPI ---
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))

# --- 모델 파일 경로 ---
MODELS_DIR = os.getenv("MODELS_DIR", "models")
EXECUTOR_MODEL_FILE = os.getenv("EXECUTOR_MODEL_FILE", "Qwen3.5-9B-Q8_0.gguf")
LIGHT_MODEL_FILE = os.getenv("LIGHT_MODEL_FILE", "Qwen3.5-0.8B.Q8_0.gguf")

# --- llama-server 바이너리 ---
LLAMA_BIN = os.getenv("LLAMA_BIN", "llama-server")

# --- 대기열 정책 ---
QUEUE_TIMEOUT_SEC = float(os.getenv("QUEUE_TIMEOUT_SEC", "60.0"))

# --- 타임아웃 ---
EXECUTOR_TIMEOUT_SEC = float(os.getenv("EXECUTOR_TIMEOUT_SEC", "120.0"))
LIGHT_TIMEOUT_SEC = float(os.getenv("LIGHT_TIMEOUT_SEC", "30.0"))
EXECUTOR_MAX_TOKENS = 2048
LIGHT_MAX_TOKENS = 500

# --- 모델 프로파일 ---
# 모델별 동작 차이를 선언적으로 관리한다.
# EXECUTOR_MODEL_NAME 소문자 substring 매칭. 미등록 모델은 _DEFAULT_PROFILE 적용.
_DEFAULT_PROFILE: dict = {
    "temperature": 0.4,
    "max_tokens": 2048,
    "think_param": None,
    "strip_think_tags": False,
}

MODEL_PROFILES: dict[str, dict] = {
    "qwen": {
        "temperature": 0.7,
        "max_tokens": 2048,
        "think_param": True,
        "strip_think_tags": True,
    },
    "glm": {
        "temperature": 0.5,
        "max_tokens": 2048,
        "think_param": None,
        "strip_think_tags": False,
    },
    "ministral": {
        "temperature": 0.4,
        "max_tokens": 2048,
        "think_param": None,
        "strip_think_tags": False,
    },
    "nemotron": {
        "temperature": 0.3,
        "max_tokens": 2048,
        "think_param": None,
        "strip_think_tags": False,
    },
}


def get_model_profile() -> dict:
    """EXECUTOR_MODEL_NAME에서 모델 패밀리를 추출하여 프로파일 반환."""
    name_lower = EXECUTOR_MODEL_NAME.lower()
    for family, profile in MODEL_PROFILES.items():
        if family in name_lower:
            return profile
    return _DEFAULT_PROFILE

# --- 서대리 페르소나 ---
PERSONA_NAME = "서영락"
PERSONA_POSITION = "대리"
PERSONA_PERSONALITY = (
    "센스있는 쾌남형. 존댓말을 사용하지만 딱딱하지 않고 편안한 톤. "
    "데이터베이스와 일정관리가 전문 분야."
)

PERSONA_SYSTEM_PROMPT = (
    "당신은 '서대리'로 불리는 AI 어시스턴트입니다. "
    f"본명은 {PERSONA_NAME}이지만, 평소에는 '서대리'로만 자신을 소개합니다. "
    "누군가 본명을 물어볼 때만 서영락이라고 답합니다.\n"
    f"{PERSONA_PERSONALITY}\n\n"
    "## 응답 포맷\n"
    "모든 응답은 반드시 아래 형식을 따르세요:\n\n"
    "1. 유저에게 보여줄 대화는 <talk></talk> 안에 넣으세요.\n"
    "2. 도구가 필요하면 <talk> 뒤에 JSON을 출력하세요.\n"
    "3. 도구가 불필요하면 <talk>만 출력하세요.\n\n"
    "예시 (도구 불필요):\n"
    "<talk>안녕하세요! 서대리입니다.</talk>\n\n"
    "예시 (도구 필요):\n"
    '<talk>네, 일정 잡아드릴게요.</talk>\n'
    '{"tool": "create_schedule", "params": {"title": "회의", "time": "10:00"}}\n\n'
    "## 대화 규칙\n"
    "1. 항상 한국어로 답변하세요.\n"
    "2. 사용자의 이전 기억이 제공되면 자연스럽게 활용하세요.\n"
    "3. 센스있고 쾌활하게, 하지만 전문적으로 답변하세요.\n"
    "4. 자기소개 시 '서대리입니다'로만. 본명은 물어볼 때만.\n"
    "5. 도구로 처리할 수 있는 요청은 반드시 도구를 호출하세요."
)

# --- 유저 등록 ---
REGISTRATION_PROMPT = (
    "처음 뵙겠습니다! 저는 서대리입니다. "
    "원활한 소통을 위해 성함, 직급, 직무를 알려주시겠어요?"
)

REGISTRATION_VALIDATION_PROMPT = (
    "Extract user info from the text. Reply in JSON format ONLY.\n"
    "Required fields: name, position, role\n"
    "If any field is missing, set it to null.\n"
    '{"name": "홍길동", "position": "과장", "role": "개발"}\n'
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

# --- 이벤트(일정) DB ---
EVENT_DB_NAME = "events.db"

# --- 0.8B 분류기 프롬프트 ---
ROUTER_SYSTEM_PROMPT = "Classify into: chat, read, think, tool. Output one word only."

# --- 0.8B 간결 페르소나 ---
LIGHT_CHAT_SYSTEM_PROMPT = (
    "당신은 '서대리' AI 어시스턴트. "
    f"본명은 {PERSONA_NAME}. "
    "센스있고 쾌활한 톤, 한국어, 1~2문장 간결 답변."
)

# --- 기억 검색 ---
MEMORY_SEARCH_PROMPT = (
    "Given the user message and available memory triples, "
    "select the most relevant triples for the response.\n"
    "Output the indices as JSON array: [0, 2, 5]\n"
    "If none are relevant, output: []\n"
    "Output ONLY the JSON array."
)
