"""파일명 → 태그 자동 추출 모듈.

파일명 패턴: {folder_number}.{weapon_base}_{variant}_{theme}_{work_stage}.{ext}
파일명을 파싱하여 태그 타입별 값을 추출하고, 에셋에 자동 연결한다.
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

# 매칭에 사용되는 작업 단계 값 목록
WORK_STAGES = {
    "원화",
    "모델링",
    "텍스처",
    "렌더",
    "인게임",
    "render",
    "texture",
    "ingame",
    "concept",
}

_WORK_STAGES_LOWER = {s.lower() for s in WORK_STAGES}


def parse_filename(filename: str) -> dict:
    """파일명에서 태그를 자동 추출한다.

    Args:
        filename: 파싱할 파일명 문자열.

    Returns:
        추출된 태그 딕셔너리. 키: folder_number, weapon_base,
        variant, work_stage. 매칭 실패 시 빈 문자열.
    """
    result = {
        "folder_number": "",
        "weapon_base": "",
        "variant": "",
        "work_stage": "",
    }

    # 첫 번째 점으로 folder_number 분리: folder_number.rest
    parts = filename.split(".", 1)
    if len(parts) < 2:
        return result

    result["folder_number"] = parts[0]

    # 확장자 제거
    name_part = parts[1].rsplit(".", 1)[0] if "." in parts[1] else parts[1]

    # 언더스코어로 세그먼트 분리
    segments = name_part.split("_")

    if len(segments) >= 1:
        result["weapon_base"] = segments[0]
    if len(segments) >= 2:
        result["variant"] = segments[1]

    # 모든 세그먼트에서 work_stage 탐색
    for seg in segments:
        if seg.lower() in _WORK_STAGES_LOWER:
            result["work_stage"] = seg
            break

    return result


def auto_tag_asset(
    conn, asset_id: int, filename: str
) -> list[str]:
    """파일명에서 추출한 태그를 에셋에 자동 연결한다.

    Args:
        conn: SQLite 연결 객체.
        asset_id: 태그를 연결할 에셋 ID.
        filename: 파싱할 파일명.

    Returns:
        연결된 태그명 목록. 형식: ['type:value', ...].
    """
    from server.data.asset_store import link_tag
    from server.data.tag_store import ensure_tag

    parsed = parse_filename(filename)
    linked: list[str] = []

    for tag_type, value in parsed.items():
        if not value:
            continue
        tag_id = ensure_tag(conn, tag_type, value)
        link_tag(conn, asset_id, tag_id)
        linked.append(f"{tag_type}:{value}")
        logger.debug("자동 태그 연결: asset_id=%d, %s:%s", asset_id, tag_type, value)

    return linked
