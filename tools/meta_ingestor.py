"""_meta.txt 인제스터. assets/ 폴더를 스캔하여 SQLite에 자동 등록한다."""

import sys

sys.path.insert(0, ".")

from pathlib import Path

from server.data.asset_store import get_assets_db, init_asset_tables, insert_asset, link_tag
from server.data.tag_store import ensure_tag, seed_tag_types
from server.domain.meta_parser import (
    extract_folder_number,
    extract_search_type_from_path,
    extract_tags_from_meta,
    parse_meta_file,
)

ASSETS_ROOT = sys.argv[1] if len(sys.argv) > 1 else "assets"


def scan_and_ingest(root: str) -> dict:
    """에셋 폴더를 스캔하고 _meta.txt 기반으로 DB에 등록한다."""
    root_path = Path(root)
    if not root_path.exists():
        print(f"[오류] 폴더 없음: {root}")
        return {"scanned": 0, "ingested": 0, "skipped": 0}

    conn = get_assets_db()
    init_asset_tables(conn)
    seed_tag_types(conn)

    scanned = 0
    ingested = 0
    skipped = 0

    for meta_file in root_path.rglob("_meta.txt"):
        scanned += 1
        folder = meta_file.parent
        folder_name = folder.name

        # 이미 등록된 에셋인지 간단히 체크 (폴더 경로 기준)
        existing = conn.execute(
            "SELECT asset_id FROM assets WHERE folder_path=?",
            (str(folder),),
        ).fetchone()
        if existing:
            skipped += 1
            continue

        # 메타 파싱
        meta = parse_meta_file(str(meta_file))
        search_type = extract_search_type_from_path(str(folder))
        folder_number = extract_folder_number(folder_name)

        # 이미지 파일 찾기
        images = list(folder.glob("*.png")) + list(folder.glob("*.jpg"))
        file_name = images[0].name if images else ""

        # 에셋 등록
        asset_id = insert_asset(
            conn, search_type, folder_number, str(folder), file_name
        )

        # 태그 연결
        tags = extract_tags_from_meta(meta)
        for tag_type, tag_value in tags:
            tag_id = ensure_tag(conn, tag_type, tag_value)
            link_tag(conn, asset_id, tag_id)

        ingested += 1
        print(f"  [{search_type}] {folder_name} — 태그 {len(tags)}개")

    conn.close()
    return {"scanned": scanned, "ingested": ingested, "skipped": skipped}


def main():
    print("=" * 50)
    print("  에셋 _meta.txt 인제스터")
    print(f"  대상 폴더: {ASSETS_ROOT}")
    print("=" * 50)
    print()

    result = scan_and_ingest(ASSETS_ROOT)

    print()
    print(f"  스캔: {result['scanned']}건")
    print(f"  등록: {result['ingested']}건")
    print(f"  건너뜀: {result['skipped']}건 (이미 등록)")
    print("  완료!")


if __name__ == "__main__":
    main()
