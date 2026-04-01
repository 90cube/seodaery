"""_meta.txt 파서. 에셋 폴더의 메타데이터 파일을 파싱한다."""

from __future__ import annotations

import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)


def parse_meta_file(meta_path: str) -> dict:
    """_meta.txt 파일을 파싱하여 키-값 딕셔너리로 반환한다.

    형식 예시:
        Name: AK-47 Dragon
        Distribution: 서든패스 S12
        Grade: Epic
        Tags: 돌격, 소총, 드래곤
    """
    result = {}
    path = Path(meta_path)
    if not path.exists():
        return result

    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = path.read_text(encoding="cp949", errors="replace")

    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            key, _, value = line.partition(":")
            result[key.strip().lower()] = value.strip()

    return result


def extract_tags_from_meta(meta: dict) -> list[tuple[str, str]]:
    """파싱된 메타데이터에서 태그 (type_name, value) 쌍을 추출한다."""
    tags = []

    # Distribution → patch_routine
    dist = meta.get("distribution", "")
    if dist:
        tags.append(("patch_routine", dist))
        # "서든패스 S12" → season 추출
        season_match = re.search(r"[Ss](\d+)", dist)
        if season_match:
            tags.append(("season", f"S{season_match.group(1)}"))

    # Grade → grade
    grade = meta.get("grade", "")
    if grade:
        tags.append(("grade", grade))

    # Tags → 개별 태그 (alias로)
    tag_str = meta.get("tags", "")
    if tag_str:
        for t in tag_str.split(","):
            t = t.strip()
            if t:
                tags.append(("alias", t))

    # Name → alias
    name = meta.get("name", "")
    if name:
        tags.append(("alias", name))

    # Work Stage
    stage = meta.get("work_stage", "") or meta.get("stage", "")
    if stage:
        tags.append(("work_stage", stage))

    return tags


def extract_search_type_from_path(folder_path: str) -> str:
    """폴더 경로에서 search_type을 추출한다."""
    path_lower = folder_path.lower()
    if "weapon" in path_lower:
        return "무기"
    if "character" in path_lower:
        return "캐릭터"
    if "item" in path_lower:
        return "아이템"
    return "기타"


def extract_folder_number(folder_name: str) -> str:
    """폴더명에서 번호를 추출한다. '001.DragonSkin' → '001'"""
    parts = folder_name.split(".", 1)
    return parts[0] if parts[0].isdigit() else folder_name
