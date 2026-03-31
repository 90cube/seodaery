# 사용자 할일 가이드

서대리 시스템 구축 후 직접 수행해야 할 작업 목록.

---

## 1. 기본 환경 (완료 확인)

- [ ] Python 3.13 설치 확인
- [ ] `setup.bat` 실행 → venv + pip install 완료
- [ ] `winget install llama.cpp` → llama-server 동작 확인
- [ ] `server/models/`에 GGUF 파일 배치
  - `Qwen3.5-0.8B-UD-Q8_K_XL.gguf`
  - `Qwen3.5-9B-Q8_0.gguf`
- [ ] `start_server.bat` → 서버 정상 기동 확인

---

## 2. 추가 패키지 설치 (Phase별)

Phase 3b 이후 기능을 사용하려면 추가 설치가 필요합니다.

```powershell
cd server
call .venv\Scripts\activate

# Phase 3b: 벡터 검색 (선택 — 없어도 텍스트 검색은 동작)
pip install watchdog==6.0.0
pip install sqlite-vss==0.1.2
pip install sentence-transformers==3.3.1
pip install open-clip-torch==2.29.0

# Phase 4: 스케줄러 (선택 — 없어도 채팅은 동작)
pip install APScheduler==3.10.4

# Phase 5: 암호화 (선택 — 없어도 평문 통신 가능)
pip install cryptography==44.0.0
```

> 모든 추가 패키지는 **선택적**. 미설치 시 해당 기능만 비활성화되고 나머지 정상 동작.

---

## 3. 데이터 투입

### 3-1. 에셋 데이터 (게임 캐릭터/무기/아이템)

**GUI 도구 사용:**
```powershell
python tools/asset_editor.py
```
- 카테고리(캐릭터/무기/아이템) 선택 → 정보 입력 → 태그 추가

**또는 Python 스크립트로 일괄 투입:**
```python
from server.data.asset_store import get_assets_db, init_asset_tables, insert_asset
from server.data.tag_store import seed_tag_types, ensure_tag
from server.data.asset_store import link_tag

conn = get_assets_db()
init_asset_tables(conn)
seed_tag_types(conn)

# 에셋 추가
aid = insert_asset(conn, "캐릭터", "675", r"\\afs\SA\675", "675.bombtechkit_v02.jpg")

# 태그 연결
tid = ensure_tag(conn, "character_class", "남캐")
link_tag(conn, aid, tid)

tid = ensure_tag(conn, "patch_routine", "서든패스")
link_tag(conn, aid, tid)

conn.close()
```

### 3-2. 지식 DB (게임 정보)

**GUI 도구:**
```powershell
python tools/knowledge_editor.py
```

**또는 스크립트:**
```python
from server.data.knowledge_store import get_knowledge_db, init_knowledge_tables, insert_knowledge

conn = get_knowledge_db()
init_knowledge_tables(conn)

insert_knowledge(conn, "character", "리퍼", "근접 암살형 캐릭터...", "암살,근접,그림자")
insert_knowledge(conn, "weapon", "AK-47", "돌격소총...", "돌격,소총,자동")
insert_knowledge(conn, "patch", "2026년 3월 패치", "신규 캐릭터 추가...", "패치,업데이트")

conn.close()
```

### 3-3. 도구 등록 (ReAct용)

```python
from server.data.tool_registry import get_tools_db, init_tool_tables, register_tool, add_param

conn = get_tools_db()
init_tool_tables(conn)

# 예: 일정 조회 도구
register_tool(conn, "get_schedule", "일정 조회", "사용자의 일정을 조회합니다")
add_param(conn, "get_schedule", "user_id", "string", required=True, description="유저 ID")
add_param(conn, "get_schedule", "date", "string", required=False, description="날짜 (YYYY-MM-DD)")

conn.close()
```

### 3-4. SKILL 등록

```python
from server.data.skill_store import get_tools_db, init_tool_tables
from server.data.skill_store import add_skill, init_skill_table

conn = get_tools_db()
init_tool_tables(conn)
init_skill_table(conn)

add_skill(
    conn,
    skill_id="sql_helper",
    name="SQL 도우미",
    description="SQL 쿼리 작성을 도와줍니다",
    instruction="사용자가 SQL 관련 질문을 하면, 정확한 SQLite 문법으로 답변하세요.",
    trigger_keywords=["SQL", "쿼리", "SELECT", "데이터베이스"],
)

conn.close()
```

---

## 4. 이미지 파일 배치

에셋과 연결할 이미지 파일:
```
server/assets/리퍼.png      ← title "리퍼"와 자동 매칭
server/assets/AK-47.png     ← title "AK-47"과 자동 매칭
```

---

## 5. 벡터 인덱싱 (Phase 3b)

패키지 설치 후 최초 1회 실행:
```powershell
python tools/asset_indexer.py
```
- CLIP 모델 다운로드 (최초 ~1분)
- 모든 에셋 이미지/텍스트 임베딩 생성
- 이후 watchdog이 실시간 동기화

---

## 6. 암호화 키 생성 (Phase 5)

```powershell
python tools/generate_key.py
```
- `shared.key` 파일 생성
- 이 파일을 클라이언트에 복사 (USB 등 오프라인)
- 서버와 클라이언트 모두 같은 키 필요

---

## 7. 네트워크 접속 허용

다른 PC에서 접속하려면:
```powershell
# 서버 시작 전 환경 변수 설정
set API_HOST=0.0.0.0
start_server.bat
```

Windows 방화벽에서 포트 8000 허용:
```powershell
netsh advfirewall firewall add rule name="서대리서버" dir=in action=allow protocol=TCP localport=8000
```

클라이언트에서:
```powershell
python client.py http://서버IP:8000
```

---

## 8. Qwen Coder 모델 추가 (검토 중)

DB 자동 관리 + 자가개선에 Qwen2.5-Coder 소형 모델 투입 검토 중.
자세한 내용은 아래 Qwen Coder 검토 섹션 참고.

---

## 문제 발생 시

| 증상 | 확인 |
|------|------|
| 서버 시작 안됨 | `llama-server --version` 확인, 모델 경로 확인 |
| 빈 응답 | `<think>` 태그 처리 확인 (llama_client.py) |
| 벡터 검색 불가 | `pip list`에서 패키지 설치 확인 |
| 암호화 실패 | `shared.key` 파일 존재 + 양쪽 동일 키 확인 |
| 다른 PC 접속 불가 | `API_HOST=0.0.0.0` 설정 + 방화벽 확인 |
