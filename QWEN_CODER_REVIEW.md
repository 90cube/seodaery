# Qwen Coder 소형 모델 투입 검토

## 후보 모델

| 모델 | 크기 | GGUF Q4 | 특징 |
|------|------|---------|------|
| Qwen2.5-Coder-1.5B | 1.5B | ~1GB | 코드 특화, SQL 생성 가능 |
| Qwen2.5-Coder-3B | 3B | ~2GB | 코드+추론 균형 |
| Qwen2.5-Coder-7B | 7B | ~4GB | 고품질, VRAM 부담 |

## 현재 VRAM 상황 (4070 Ti Super 16GB)

```
0.8B 라우터     ≈  1.2 GB
9B 실행기       ≈  9.3 GB
KV cache        ≈  1-2 GB
────────────────────────
현재 사용       ≈ 11.5-12.5 GB
여유            ≈  3.5-4.5 GB
```

## 투입 가능성

### 옵션 A: Qwen2.5-Coder-1.5B (Q4, ~1GB) ← 추천

```
기존            ≈ 12 GB
+ Coder 1.5B   ≈  1 GB
────────────────────
합계            ≈ 13 GB (여유 3GB) ✓
```

**가능.** 3번째 llama-server 인스턴스(포트 8083)로 상시 상주.

### 옵션 B: Qwen2.5-Coder-3B (Q4, ~2GB)

```
합계 ≈ 14 GB (여유 2GB) — 빡빡하지만 가능
```

### 옵션 C: Qwen2.5-Coder-7B — VRAM 초과. 불가.

---

## 역할 배분 (3모델 체제)

```
사용자 입력
    │
    ▼
0.8B 라우터 (:8081) → 입력 분류
    │
    ├─ 일반 대화 → 9B 실행기 (:8082)
    │
    ├─ SQL/코드 → Coder 1.5B (:8083) → 결과를 9B에 전달
    │
    └─ 도구 호출 → 9B ReAct 루프
```

## 활용 시나리오

### 1. DB 자동 관리 (SQLite 쿼리 생성)

```
사용자: "지난달 패치에 추가된 캐릭터 목록 알려줘"
    │
    ▼
0.8B: "SQL 쿼리 필요" 판단
    │
    ▼
Coder 1.5B: 스키마 정보 + 질문 → SQL 생성
    "SELECT a.* FROM assets a JOIN asset_tags at ON ...
     WHERE tag_type='patch_date' AND value LIKE '2026-02%'"
    │
    ▼
Python: SQL 실행 → 결과
    │
    ▼
9B: 결과를 자연어로 정리하여 사용자에게 응답
```

**장점**: 9B가 직접 SQL 짜는 것보다 Coder가 더 정확하고 빠름.

### 2. 자가개선 (프롬프트 최적화)

```
서과장 autoresearch 루프:
    │
    ▼
Coder 1.5B: 테스트 케이스 → 도구 호출 JSON 생성
    │
    ▼
5단계 검증: 성공/실패 판정
    │
    ▼
메트릭 기록: 정답률 측정
    │
    ▼
프롬프트 변형 → 반복
```

**장점**: Claude Code나 9B를 소모하지 않고 저비용으로 실험 가능.

### 3. 온톨로지 자동 정리

```
새 에셋 파일 감지 (watchdog)
    │
    ▼
Coder 1.5B: 파일명 분석 → 태그 추천
    "675.bombtechkit_v02.jpg"
    → {"weapon_base": "bombtechkit", "variant": "v02", "work_stage": "render"}
    │
    ▼
Python: 태그 자동 연결
```

---

## 구현 방법 (기존 코드에 융합)

### constants.py 추가

```python
CODER_MODEL_URL = os.getenv("CODER_MODEL_URL", "http://localhost:8083")
CODER_MODEL_NAME = os.getenv("CODER_MODEL_NAME", "qwen2.5-coder-1.5b")
CODER_MODEL_FILE = os.getenv("CODER_MODEL_FILE", "Qwen2.5-Coder-1.5B-Q4_K_M.gguf")
CODER_CTX_SIZE = int(os.getenv("CODER_CTX_SIZE", "4096"))
CODER_GPU_LAYERS = int(os.getenv("CODER_GPU_LAYERS", "99"))
CODER_TIMEOUT_SEC = float(os.getenv("CODER_TIMEOUT_SEC", "30.0"))
```

### process_manager.py 변경

3번째 모델 프로세스 추가 (포트 8083).

### 신규 파일

| 파일 | 역할 |
|------|------|
| `server/domain/coder_agent.py` | Coder 모델 호출 래퍼 (SQL 생성, 코드 생성, 태그 추천) |
| `server/domain/sql_executor.py` | 생성된 SQL을 안전하게 실행 (SELECT만 허용, 화이트리스트) |

---

## 결론

**Qwen2.5-Coder-1.5B Q4 투입 추천.**

- VRAM 1GB 추가로 3모델 체제 가능
- DB 쿼리 생성, 자가개선 실험, 온톨로지 정리에 즉시 활용
- 9B의 부담을 줄이고 전문 작업 분리

다음 단계: 모델 다운로드 + constants/process_manager 수정 + coder_agent 구현.
